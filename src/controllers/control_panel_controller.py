import asyncio
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent
from models.enums import EncoderSource, ButtonID
from components.control_panel import ControlPanel
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory

log = get_logger()

class ControlPanelController:
    """
    Controller for the hardware Control Panel

    Polls hardware inputs and publishes events to the EventBus.
    """

    def __init__(self, control_panel: ControlPanel, event_bus: EventBus):
        """
        Initialize ControlPanelController

        Args:
            control_panel: ControlPanel instance for hardware interaction
            event_bus: EventBus for publishing hardware events
        """
        self.control_panel = control_panel
        self.event_bus = event_bus
        self._running = False
        
    async def poll(self, interval: float = 0.02):
        """
        Run the control panel polling loop

        Args:
            interval: Polling interval in seconds (default 0.02s = 50Hz)
        """
        self._running = True
        log.info(LogCategory.HARDWARE, "ControlPanelController started polling loop")
        
        while self._running:
            self._poll_encoders()
            self._poll_buttons()
            await asyncio.sleep(interval)
        
    def _poll_encoders(self):
        """
        Poll encoders and publish events on changes
        """
        
        for src, encoder in (
            (EncoderSource.SELECTOR, self.control_panel.selector),
            (EncoderSource.MODULATOR, self.control_panel.modulator)
        ):
            # Rotation
            delta = encoder.read()
            if delta:
                event = EncoderRotateEvent(src, delta)
                asyncio.create_task(self.event_bus.publish(event))
            
            # Button press
            if encoder.is_pressed():
                event = EncoderClickEvent(src)
                asyncio.create_task(self.event_bus.publish(event))
                
    def _poll_buttons(self):
        """
        Poll buttons and publish events on changes
        """
        # Buttons (map index to ButtonID enum)
        button_ids = [ButtonID.BTN1, ButtonID.BTN2, ButtonID.BTN3, ButtonID.BTN4]
        
        for i, btn in enumerate(self.control_panel.buttons):
            if btn.is_pressed():
                event = ButtonPressEvent(button_ids[i])
                asyncio.create_task(self.event_bus.publish(event))
                
    def stop(self):
        """
        Stop the control panel polling loop
        """
        self._running = False
        log.info(LogCategory.HARDWARE, "ControlPanelController stopped polling loop")