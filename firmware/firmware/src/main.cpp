#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include "secrets.h"

const int MOSFET_PIN = 23;

const int PWM_CHANNEL = 0;
const int PWM_FREQUENCY = 5000;
const int PWM_RESOLUTION = 8;

const unsigned long BRIGHTNESS_STEP_INTERVAL_MILLISECONDS = 10;
const unsigned long HOLD_INTERVAL_MILLISECONDS = 500;
const unsigned long HEARTBEAT_INTERVAL_MILLISECONDS = 5000;
const unsigned long WIFI_CONNECT_TIMEOUT_MILLISECONDS = 15000;
const unsigned long WIFI_RECONNECT_RETRY_INTERVAL_MILLISECONDS = 5000;
const unsigned long RPI_DISCOVERY_RETRY_INTERVAL_MILLISECONDS = 10000;
const uint32_t MDNS_QUERY_TIMEOUT_MILLISECONDS = 2000;

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
                resolveRpiAddress();
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
                // The WiFi interface mDNS is bound to is gone - restart both after reconnecting.
                mdnsStarted = false;
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
    unsigned long now = millis();

    switch (breathePhase) {
        case BreathePhase::BRIGHTENING:
            if (now - lastBrightnessStepTime >= BRIGHTNESS_STEP_INTERVAL_MILLISECONDS) {
                lastBrightnessStepTime = now;
                currentBrightness++;
                ledcWrite(PWM_CHANNEL, currentBrightness);
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
                ledcWrite(PWM_CHANNEL, currentBrightness);
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
        + "\"firmware\":\"diuna-esp32-poc\""
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

    // Konfiguracja kanału PWM
    ledcSetup(
        PWM_CHANNEL,
        PWM_FREQUENCY,
        PWM_RESOLUTION
    );

    // Przypisanie kanału PWM do GPIO23
    ledcAttachPin(
        MOSFET_PIN,
        PWM_CHANNEL
    );

    Serial.println("ESP32 MOSFET PWM test");

    beginWifiConnectionAttempt();

    lastBrightnessStepTime = millis();
    phaseStartTime = millis();
    lastHeartbeatTime = millis();
}

void loop() {
    updateWifiConnection();
    updateRpiDiscovery();
    updateBreatheAnimation();

    unsigned long now = millis();
    if (now - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MILLISECONDS) {
        lastHeartbeatTime = now;
        sendHeartbeat();
    }
}
