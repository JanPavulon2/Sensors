Tagi technologiczne: #tech/(esp32, raspberry-pi, rpi5, rpi4, rpi2, relay, sensor, led, led-strip) - używać zawsze przy modułach i sprzęcie. Proponuj nowe tagi gdy pojawi się nowa kategoria (np. sensor/capacitive, display/oled, motor/stepper)
Module naming: {Module code} ({english desc}).md -- English by default, Polish only in parantheses
Module photos: vault/_media/moduły/{MODULE-CODE}/
§
User is working alone on Aurora project (LED control system). Main current goal: transition from single-device to multi-device architecture (host/node split). Other planned enhancements: 2D LED mapping (shape-based), ESP32 as remote rendering nodes. User wants orchestrator agent that understands project, delegates work, learns over time, and suggests improvements. Prefers proactive guidance over passive execution.
§
Aurora System Understanding:
- Current: Single-host Raspberry Pi system with 60 FPS render loop, zone-based control, animations, web frontend
- Planned: Multi-device architecture with rpi5-host, esp32-node, rpi4-node
- Key Systems: FrameManager (priority queues), ZoneService, AnimationEngine, EventBus, FastAPI + Socket.IO
- Enhancements Needed: Host/node split, 2D LED mapping, ESP32 remote rendering, communication protocol (WebAPI + ?), synchronization
- User wants orchestrator agent for strategic planning, workflow guidance, technical understanding, vision ideas, and realistic feedback
- User works alone, prefers proactive guidance, explanations before acting, and wants agent to learn and suggest improvements
§
Aurora project context: Single-host Raspberry Pi system transitioning to multi-device architecture (rpi5-host, esp32-node, rpi4-node). Key systems: FrameManager (priority queues), ZoneService, AnimationEngine, EventBus, FastAPI + Socket.IO. Current goal: host/node split, 2D LED mapping, ESP32 remote rendering. User prefers proactive guidance, explanations before acting, wants agent to learn and suggest improvements. Module naming: {Module code} ({english desc}).md in vault/_media/moduły/{MODULE-CODE}/.