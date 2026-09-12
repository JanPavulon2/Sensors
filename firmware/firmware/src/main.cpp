#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include "time.h"
#include "secrets.h"
#include "led_config.h"

const unsigned long BRIGHTNESS_STEP_INTERVAL_MILLISECONDS = 10;
const unsigned long HOLD_INTERVAL_MILLISECONDS = 500;
const unsigned long HEARTBEAT_INTERVAL_MILLISECONDS = 5000;
const unsigned long WIFI_CONNECT_TIMEOUT_MILLISECONDS = 15000;
const unsigned long WIFI_RECONNECT_RETRY_INTERVAL_MILLISECONDS = 5000;
const unsigned long RPI_DISCOVERY_RETRY_INTERVAL_MILLISECONDS = 10000;
const uint32_t MDNS_QUERY_TIMEOUT_MILLISECONDS = 2000;
const unsigned long IDENTIFY_BLINK_INTERVAL_MILLISECONDS = 150;
const unsigned long IDENTIFY_DURATION_MILLISECONDS = 2000;
const char* SYNC_MULTICAST_GROUP_ADDRESS = "239.255.10.10";
const uint16_t SYNC_MULTICAST_PORT = 41234;
const unsigned long DEFAULT_BREATHE_CYCLE_DURATION_MILLISECONDS = 2400;

enum class BreathePhase {
    BRIGHTENING,
    HOLDING_BRIGHT,
    DIMMING,
    HOLDING_DIM,
};

enum class WifiConnectionState {
    CONNECTING,
    CONNECTED,
    RECONNECT_PENDING,
};

BreathePhase breathePhase = BreathePhase::BRIGHTENING;
int currentBrightness = 0;
unsigned long lastBrightnessStepTime = 0;
unsigned long phaseStartTime = 0;

unsigned long lastHeartbeatTime = 0;

WifiConnectionState wifiConnectionState = WifiConnectionState::CONNECTING;
unsigned long wifiConnectAttemptStartTime = 0;
unsigned long wifiReconnectPendingSinceTime = 0;

bool mdnsStarted = false;
bool rpiAddressKnown = false;
IPAddress rpiAddress;
unsigned long lastRpiDiscoveryAttemptTime = 0;

WebServer commandServer(NODE_COMMAND_PORT);

bool identifyActive = false;
unsigned long identifyStartTime = 0;
unsigned long lastIdentifyToggleTime = 0;
bool identifyLedIsOn = false;

#if USE_ADDRESSABLE_STRIP
CRGB ledStripPixels[LED_STRIP_PIXEL_COUNT];
#else
// Original single MOSFET-dimmed LED (no addressable strip attached yet).
const int MOSFET_PIN = 23;
const int PWM_CHANNEL = 0;
const int PWM_FREQUENCY = 5000;
const int PWM_RESOLUTION = 8;
#endif

struct RemoteZoneState {
    bool isOn = true;
    uint8_t brightness = 100;
    uint8_t red = 255;
    uint8_t green = 255;
    uint8_t blue = 255;
    bool useBreatheAnimation = false;
};

RemoteZoneState remoteZoneState;

WiFiUDP syncUdp;
bool syncListenerStarted = false;
bool phaseReferenceKnown = false;
unsigned long phaseReferenceEpochMilliseconds = 0;
unsigned long phaseCycleDurationMilliseconds = DEFAULT_BREATHE_CYCLE_DURATION_MILLISECONDS;

// Initializes whichever physical LED output is currently wired up - see
// USE_ADDRESSABLE_STRIP in led_config.h.
void beginLedOutput() {
#if USE_ADDRESSABLE_STRIP
    FastLED.addLeds<WS2812B, LED_STRIP_DATA_PIN, GRB>(ledStripPixels, LED_STRIP_PIXEL_COUNT);
    Serial.println("FastLED strip initialized");
#else
    ledcSetup(PWM_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
    ledcAttachPin(MOSFET_PIN, PWM_CHANNEL);
    Serial.println("MOSFET-dimmed single LED initialized (no addressable strip attached yet)");
#endif
}

// Single seam between "what color/brightness should be shown" and "how to
// physically show it" - every other function in this file goes through
// here instead of touching FastLED/ledcWrite directly, so
// USE_ADDRESSABLE_STRIP only needs to be handled in one place. On the
// single MOSFET-dimmed LED, only brightness matters (it can't reproduce
// hue), so the brightest of the three channels drives the PWM duty cycle.
void applyOutputColor(uint8_t red, uint8_t green, uint8_t blue) {
#if USE_ADDRESSABLE_STRIP
    fill_solid(ledStripPixels, LED_STRIP_PIXEL_COUNT, CRGB(red, green, blue));
    FastLED.show();
#else
    uint8_t peakChannelValue = max(red, max(green, blue));
    ledcWrite(PWM_CHANNEL, peakChannelValue);
#endif
}

// Builds a per-device mDNS hostname from the MAC address so multiple ESP32
// nodes on the same LAN don't collide on one shared name.
String buildEsp32MdnsHostname() {
    String mac = WiFi.macAddress();
    mac.replace(":", "");
    return "diuna-esp32-" + mac.substring(6);
}

// mDNS must be (re)started on the current WiFi interface before queryHost()
// works, so this runs once per successful connection, not once per boot.
void beginMdnsIfNeeded() {
    if (mdnsStarted) {
        return;
    }

    String hostname = buildEsp32MdnsHostname();
    if (MDNS.begin(hostname.c_str())) {
        Serial.print("mDNS started, this node is reachable as ");
        Serial.print(hostname);
        Serial.println(".local");
        mdnsStarted = true;
    } else {
        Serial.println("mDNS failed to start, will retry next loop");
    }
}

bool otaStarted = false;

// OTA needs mDNS already running for the hostname to resolve, so this is
// called right after beginMdnsIfNeeded() on each successful connection.
void beginOtaIfNeeded() {
    if (otaStarted) {
        return;
    }

    ArduinoOTA.setHostname(buildEsp32MdnsHostname().c_str());
    ArduinoOTA.begin();
    otaStarted = true;
    Serial.println("ArduinoOTA started");
}

// Resolves RPI_MDNS_HOSTNAME to a live IP over mDNS, replacing the old
// hardcoded RPI_HOST. Lets a new ESP32 be flashed without knowing the RPi5's
// current DHCP-assigned address in advance.
void resolveRpiAddress() {
    lastRpiDiscoveryAttemptTime = millis();

    Serial.print("Resolving RPi5 via mDNS: ");
    Serial.println(RPI_MDNS_HOSTNAME);

    IPAddress resolved = MDNS.queryHost(RPI_MDNS_HOSTNAME, MDNS_QUERY_TIMEOUT_MILLISECONDS);
    if (resolved == INADDR_NONE) {
        Serial.println("mDNS discovery failed, will retry");
        rpiAddressKnown = false;
        return;
    }

    rpiAddress = resolved;
    rpiAddressKnown = true;
    Serial.print("Resolved RPi5 address: ");
    Serial.println(rpiAddress);
}

// NTP sync must follow a successful WiFi connection (mirrors
// beginMdnsIfNeeded()'s "runs once per connection" pattern) - the multicast
// join also needs a live interface.
void beginSyncListenerIfNeeded() {
    if (syncListenerStarted) {
        return;
    }

    configTime(0, 0, "pool.ntp.org");
    IPAddress multicastGroup;
    multicastGroup.fromString(SYNC_MULTICAST_GROUP_ADDRESS);
    if (syncUdp.beginMulticast(multicastGroup, SYNC_MULTICAST_PORT)) {
        syncListenerStarted = true;
        Serial.println("NTP + sync multicast listener started");
    }
}

unsigned long currentEpochMilliseconds() {
    time_t now;
    time(&now);
    return (unsigned long)now * 1000UL;
}

void updateSyncListener() {
    int packetSize = syncUdp.parsePacket();
    if (packetSize <= 0) {
        return;
    }

    char packetBuffer[256];
    int bytesRead = syncUdp.read(packetBuffer, sizeof(packetBuffer) - 1);
    if (bytesRead <= 0) {
        return;
    }
    packetBuffer[bytesRead] = '\0';

    JsonDocument syncDocument;
    if (deserializeJson(syncDocument, packetBuffer)) {
        return;
    }

    const char* syncGroup = syncDocument["sync_group"] | "";
    if (strcmp(syncGroup, NODE_SYNC_GROUP) != 0) {
        return;  // not our group - ignore
    }

    phaseReferenceEpochMilliseconds = syncDocument["reference_epoch_ms"] | 0;
    phaseCycleDurationMilliseconds = syncDocument["cycle_duration_ms"] | DEFAULT_BREATHE_CYCLE_DURATION_MILLISECONDS;
    phaseReferenceKnown = true;
}

// Triangle wave over the shared cycle, driven by NTP-synced wall-clock time
// instead of this device's own millis() - the actual "lockstep" mechanism.
uint8_t computeSyncedBreatheBrightness() {
    unsigned long elapsedMilliseconds =
        (currentEpochMilliseconds() - phaseReferenceEpochMilliseconds) % phaseCycleDurationMilliseconds;
    unsigned long halfCycleMilliseconds = phaseCycleDurationMilliseconds / 2;

    if (elapsedMilliseconds < halfCycleMilliseconds) {
        return (uint8_t)map(elapsedMilliseconds, 0, halfCycleMilliseconds, 0, 255);
    }
    return (uint8_t)map(elapsedMilliseconds - halfCycleMilliseconds, 0, halfCycleMilliseconds, 255, 0);
}

// Non-blocking: kicks off a connection attempt and returns immediately.
// Actual connect/timeout/retry handling happens in updateWifiConnection().
void beginWifiConnectionAttempt() {
    Serial.print("Connecting to WiFi network: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    wifiConnectAttemptStartTime = millis();
    wifiConnectionState = WifiConnectionState::CONNECTING;
}

// State machine (mirrors updateBreatheAnimation()'s non-blocking millis() pattern):
// CONNECTING -> CONNECTED on success, or RECONNECT_PENDING on timeout.
// CONNECTED -> RECONNECT_PENDING if the link drops mid-run.
// RECONNECT_PENDING -> CONNECTING after a retry backoff, so a dropped WiFi
// connection recovers on its own instead of leaving the node stuck forever.
void updateWifiConnection() {
    unsigned long now = millis();

    switch (wifiConnectionState) {
        case WifiConnectionState::CONNECTING:
            if (WiFi.status() == WL_CONNECTED) {
                Serial.print("WiFi connected, IP address: ");
                Serial.println(WiFi.localIP());
                wifiConnectionState = WifiConnectionState::CONNECTED;
                beginMdnsIfNeeded();
                beginOtaIfNeeded();
                resolveRpiAddress();
                beginSyncListenerIfNeeded();
            } else if (now - wifiConnectAttemptStartTime >= WIFI_CONNECT_TIMEOUT_MILLISECONDS) {
                Serial.println("WiFi connect attempt timed out, will retry");
                wifiReconnectPendingSinceTime = now;
                wifiConnectionState = WifiConnectionState::RECONNECT_PENDING;
            }
            break;

        case WifiConnectionState::CONNECTED:
            if (WiFi.status() != WL_CONNECTED) {
                Serial.println("WiFi connection lost, will attempt to reconnect");
                wifiReconnectPendingSinceTime = now;
                wifiConnectionState = WifiConnectionState::RECONNECT_PENDING;
                // The WiFi interface mDNS/OTA are bound to is gone - restart after reconnecting.
                mdnsStarted = false;
                otaStarted = false;
                rpiAddressKnown = false;
            }
            break;

        case WifiConnectionState::RECONNECT_PENDING:
            if (now - wifiReconnectPendingSinceTime >= WIFI_RECONNECT_RETRY_INTERVAL_MILLISECONDS) {
                beginWifiConnectionAttempt();
            }
            break;
    }
}

// Retries mDNS discovery on its own timer whenever the RPi5's address isn't
// currently known (first boot before it responds, or after a failed lookup).
void updateRpiDiscovery() {
    if (wifiConnectionState != WifiConnectionState::CONNECTED || rpiAddressKnown) {
        return;
    }

    unsigned long now = millis();
    if (now - lastRpiDiscoveryAttemptTime >= RPI_DISCOVERY_RETRY_INTERVAL_MILLISECONDS) {
        resolveRpiAddress();
    }
}

void updateBreatheAnimation() {
    if (!remoteZoneState.useBreatheAnimation) {
        return;
    }

    if (phaseReferenceKnown) {
        uint8_t syncedBrightness = computeSyncedBreatheBrightness();
        applyOutputColor(
            (uint16_t)remoteZoneState.red * syncedBrightness / 255,
            (uint16_t)remoteZoneState.green * syncedBrightness / 255,
            (uint16_t)remoteZoneState.blue * syncedBrightness / 255
        );
        return;
    }

    // Fallback: no sync reference yet (first boot, or this node isn't in a
    // sync_group) - use the local millis() state machine unchanged.
    unsigned long now = millis();

    switch (breathePhase) {
        case BreathePhase::BRIGHTENING:
            if (now - lastBrightnessStepTime >= BRIGHTNESS_STEP_INTERVAL_MILLISECONDS) {
                lastBrightnessStepTime = now;
                currentBrightness++;
                applyOutputColor(
                    (uint16_t)remoteZoneState.red * currentBrightness / 255,
                    (uint16_t)remoteZoneState.green * currentBrightness / 255,
                    (uint16_t)remoteZoneState.blue * currentBrightness / 255
                );
                if (currentBrightness >= 255) {
                    breathePhase = BreathePhase::HOLDING_BRIGHT;
                    phaseStartTime = now;
                }
            }
            break;

        case BreathePhase::HOLDING_BRIGHT:
            if (now - phaseStartTime >= HOLD_INTERVAL_MILLISECONDS) {
                breathePhase = BreathePhase::DIMMING;
            }
            break;

        case BreathePhase::DIMMING:
            if (now - lastBrightnessStepTime >= BRIGHTNESS_STEP_INTERVAL_MILLISECONDS) {
                lastBrightnessStepTime = now;
                currentBrightness--;
                applyOutputColor(
                    (uint16_t)remoteZoneState.red * currentBrightness / 255,
                    (uint16_t)remoteZoneState.green * currentBrightness / 255,
                    (uint16_t)remoteZoneState.blue * currentBrightness / 255
                );
                if (currentBrightness <= 0) {
                    breathePhase = BreathePhase::HOLDING_DIM;
                    phaseStartTime = now;
                }
            }
            break;

        case BreathePhase::HOLDING_DIM:
            if (now - phaseStartTime >= HOLD_INTERVAL_MILLISECONDS) {
                breathePhase = BreathePhase::BRIGHTENING;
            }
            break;
    }
}

void beginIdentifyBlink() {
    identifyActive = true;
    identifyStartTime = millis();
    lastIdentifyToggleTime = millis();
    identifyLedIsOn = false;
    Serial.println("Identify command received - blinking");
}

// Takes priority over the normal breathe/zone-state rendering while active -
// loop() only calls updateBreatheAnimation() when this returns false.
bool updateIdentifyBlink() {
    if (!identifyActive) {
        return false;
    }

    unsigned long now = millis();
    if (now - identifyStartTime >= IDENTIFY_DURATION_MILLISECONDS) {
        identifyActive = false;
        return false;
    }

    if (now - lastIdentifyToggleTime >= IDENTIFY_BLINK_INTERVAL_MILLISECONDS) {
        lastIdentifyToggleTime = now;
        identifyLedIsOn = !identifyLedIsOn;
        uint8_t identifyChannelValue = identifyLedIsOn ? 255 : 0;
        applyOutputColor(identifyChannelValue, identifyChannelValue, identifyChannelValue);
    }
    return true;
}

void applyRemoteZoneStateToStrip() {
    if (!remoteZoneState.isOn) {
        applyOutputColor(0, 0, 0);
        return;
    }

    applyOutputColor(
        (uint16_t)remoteZoneState.red * remoteZoneState.brightness / 100,
        (uint16_t)remoteZoneState.green * remoteZoneState.brightness / 100,
        (uint16_t)remoteZoneState.blue * remoteZoneState.brightness / 100
    );
}

void applyZoneStateCommand(JsonObject payload) {
    remoteZoneState.isOn = payload["is_on"] | true;
    remoteZoneState.brightness = payload["brightness"] | 100;

    JsonObject color = payload["color"];
    remoteZoneState.red = color["r"] | 255;
    remoteZoneState.green = color["g"] | 255;
    remoteZoneState.blue = color["b"] | 255;

    const char* renderModeText = payload["render_mode"] | "STATIC";
    remoteZoneState.useBreatheAnimation = (strcmp(renderModeText, "BREATHE") == 0);

    if (!remoteZoneState.useBreatheAnimation) {
        applyRemoteZoneStateToStrip();
    }
}

void handleCommandRequest() {
    if (commandServer.method() != HTTP_POST) {
        commandServer.send(405, "application/json", "{\"error\":\"method not allowed\"}");
        return;
    }

    String requestBody = commandServer.arg("plain");
    JsonDocument commandDocument;
    DeserializationError parseError = deserializeJson(commandDocument, requestBody);
    if (parseError) {
        commandServer.send(400, "application/json", "{\"error\":\"invalid json\"}");
        return;
    }

    String commandName = commandDocument["name"] | "";

    if (commandName == "identify") {
        beginIdentifyBlink();
    } else if (commandName == "zone.state") {
        applyZoneStateCommand(commandDocument["payload"].as<JsonObject>());
    } else {
        // Unknown command names are rejected rather than silently ignored,
        // so a misconfigured RPi command gets a visible error instead of nothing.
        commandServer.send(400, "application/json", "{\"error\":\"unknown command\"}");
        return;
    }

    commandServer.send(200, "application/json", "{\"status\":\"ok\"}");
}

void beginCommandServer() {
    commandServer.on("/command", HTTP_POST, handleCommandRequest);
    commandServer.begin();
    Serial.print("Command server listening on port ");
    Serial.println(NODE_COMMAND_PORT);
}

void sendHeartbeat() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Heartbeat skipped: WiFi not connected");
        return;
    }

    if (!rpiAddressKnown) {
        Serial.println("Heartbeat skipped: RPi5 address not yet resolved via mDNS");
        return;
    }

    HTTPClient httpClient;
    String url = String("http://") + rpiAddress.toString() + ":" + RPI_PORT + "/api/v1/nodes/heartbeat";
    httpClient.begin(url);
    httpClient.addHeader("Content-Type", "application/json");
    httpClient.addHeader("X-Node-Secret", NODE_SHARED_SECRET);

    String payload = String("{")
        + "\"node_id\":\"" + WiFi.macAddress() + "\","
        + "\"node_type\":\"ESP32\","
        + "\"address\":\"" + WiFi.localIP().toString() + "\","
        + "\"command_port\":" + NODE_COMMAND_PORT + ","
        + "\"firmware\":\"diuna-esp32-poc\","
        + "\"capabilities\":[\"render_output\",\"command_execution\",\"telemetry_publish\"]"
        + "}";

    int responseCode = httpClient.POST(payload);
    Serial.print("Heartbeat sent, HTTP ");
    Serial.println(responseCode);

    if (responseCode <= 0) {
        // Transport-level failure (not just a non-2xx HTTP status) - the resolved
        // address is likely stale (e.g. RPi5 got a new DHCP lease). Re-resolve.
        Serial.println("Heartbeat transport failed, will re-resolve RPi5 address via mDNS");
        rpiAddressKnown = false;
    }

    httpClient.end();
}

void setup() {
    Serial.begin(115200);

    beginLedOutput();

    beginWifiConnectionAttempt();
    beginCommandServer();

    lastBrightnessStepTime = millis();
    phaseStartTime = millis();
    lastHeartbeatTime = millis();
}

void loop() {
    updateWifiConnection();
    updateRpiDiscovery();
    updateSyncListener();
    commandServer.handleClient();
    ArduinoOTA.handle();

    if (!updateIdentifyBlink()) {
        updateBreatheAnimation();
    }

    unsigned long now = millis();
    if (now - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MILLISECONDS) {
        lastHeartbeatTime = now;
        sendHeartbeat();
    }
}
