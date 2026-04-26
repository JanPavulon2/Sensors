#!/usr/bin/env python3
"""
Real integration tests for keyboard adapter system

These tests import and test the actual adapter implementations,
verifying real-world scenarios like:
- Factory selection logic (evdev → stdin → dummy)
- Adapter initialization
- Event publishing through real EventBus
- Environment detection
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest
import anyio

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.event_bus import EventBus
from models.events import KeyboardKeyPressEvent, EventType
from hardware.input.keyboard.adapters.dummy import DummyKeyboardAdapter
from hardware.input.keyboard.adapters.stdin import StdinKeyboardAdapter
from hardware.input.keyboard.adapters.evdev import EvdevKeyboardAdapter
from hardware.input.keyboard.factory import start_keyboard


# ============================================================================
# Real Adapter Tests
# ============================================================================

class TestDummyKeyboardAdapterReal:
    """Test real DummyKeyboardAdapter implementation"""

    @pytest.mark.asyncio
    async def test_dummy_adapter_runs_without_emitting(self):
        """Dummy adapter should run indefinitely without emitting events"""
        event_bus = EventBus()
        adapter = DummyKeyboardAdapter(event_bus)

        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler)

        # Run for a short time
        task = asyncio.create_task(adapter.run())
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_dummy_adapter_handles_cancellation(self):
        """Dummy adapter should handle cancellation gracefully"""
        event_bus = EventBus()
        adapter = DummyKeyboardAdapter(event_bus)

        task = asyncio.create_task(adapter.run())
        await asyncio.sleep(0.05)
        task.cancel()

        # Should not raise unhandled exception
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected


class TestEvdevKeyboardAdapterReal:
    """Test real EvdevKeyboardAdapter with mocked hardware"""

    def test_evdev_adapter_initialization(self):
        """EvdevKeyboardAdapter should initialize with correct default state"""
        event_bus = EventBus()
        adapter = EvdevKeyboardAdapter(event_bus, device_path="/dev/input/event0")

        assert adapter.device_path == "/dev/input/event0"
        assert adapter._modifiers == {"CTRL": False, "SHIFT": False, "ALT": False}
        assert adapter.device is None  # Not opened until run()

    def test_normalize_key_name(self):
        """Test key name normalization logic"""
        event_bus = EventBus()
        adapter = EvdevKeyboardAdapter(event_bus)

        # Regular keys
        assert adapter._normalize_key_name("KEY_A") == "A"
        assert adapter._normalize_key_name("KEY_ENTER") == "ENTER"
        assert adapter._normalize_key_name("KEY_SPACE") == "SPACE"

        # Pure modifiers should be filtered out
        assert adapter._normalize_key_name("KEY_LEFTSHIFT") == ""
        assert adapter._normalize_key_name("KEY_RIGHTCTRL") == ""
        assert adapter._normalize_key_name("KEY_LEFTALT") == ""

    def test_modifier_state_tracking(self):
        """Test modifier state updates"""
        event_bus = EventBus()
        adapter = EvdevKeyboardAdapter(event_bus)

        # Press CTRL
        adapter._update_modifier_state("KEY_LEFTCTRL", pressed=True)
        assert adapter._modifiers["CTRL"] is True

        # Release CTRL
        adapter._update_modifier_state("KEY_LEFTCTRL", pressed=False)
        assert adapter._modifiers["CTRL"] is False

        # Multiple modifiers
        adapter._update_modifier_state("KEY_LEFTSHIFT", pressed=True)
        adapter._update_modifier_state("KEY_RIGHTALT", pressed=True)
        assert adapter._modifiers["SHIFT"] is True
        assert adapter._modifiers["ALT"] is True

    @pytest.mark.asyncio
    async def test_evdev_adapter_publishes_events(self):
        """Test that evdev adapter publishes KeyboardKeyPressEvent"""
        event_bus = EventBus()
        adapter = EvdevKeyboardAdapter(event_bus)

        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler)

        # Create mock key event
        with patch('hardware.input.keyboard.adapters.evdev.ecodes') as mock_ecodes:
            mock_ecodes.EV_KEY = 1
            mock_ecodes.bytype = {1: {30: 'KEY_A'}}

            key_event = MagicMock()
            key_event.type = 1  # EV_KEY
            key_event.code = 30  # KEY_A
            key_event.value = 1  # Key down

            await adapter._handle_key_event(key_event)

        assert len(received_events) == 1
        assert received_events[0].key == "A"
        assert received_events[0].modifiers == []

    @pytest.mark.asyncio
    async def test_evdev_adapter_raises_when_no_device(self):
        """Test that adapter raises RuntimeError if no keyboard device found"""
        event_bus = EventBus()
        adapter = EvdevKeyboardAdapter(event_bus)

        with patch('hardware.input.keyboard.adapters.evdev.list_devices', return_value=[]):
            with pytest.raises(RuntimeError, match="No evdev keyboard available"):
                await adapter.run()


class TestStdinKeyboardAdapterReal:
    """Test real StdinKeyboardAdapter with mocked stdin"""

    @pytest.mark.asyncio
    async def test_stdin_adapter_raises_if_not_tty(self):
        """StdinKeyboardAdapter should raise if stdin is not a TTY"""
        event_bus = EventBus()
        adapter = StdinKeyboardAdapter(event_bus)

        with patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False

            with pytest.raises(RuntimeError, match="STDIN is not a TTY"):
                await adapter.run()

    @pytest.mark.asyncio
    async def test_stdin_adapter_processes_arrow_keys(self):
        """Test arrow key escape sequence processing"""
        event_bus = EventBus()
        adapter = StdinKeyboardAdapter(event_bus)

        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler)

        # Test all arrow keys
        arrow_sequences = [
            ('\x1b[A', 'UP'),
            ('\x1b[B', 'DOWN'),
            ('\x1b[C', 'RIGHT'),
            ('\x1b[D', 'LEFT'),
        ]

        for seq, expected_key in arrow_sequences:
            adapter._buffer = seq
            await adapter._process_buffer()

        assert len(received_events) == 4
        assert [e.key for e in received_events] == ['UP', 'DOWN', 'RIGHT', 'LEFT']

    @pytest.mark.asyncio
    async def test_stdin_adapter_detects_ctrl_keys(self):
        """Test Ctrl+Key detection"""
        event_bus = EventBus()
        adapter = StdinKeyboardAdapter(event_bus)

        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler)

        # Ctrl+A (0x01) and Ctrl+C (0x03)
        adapter._buffer = '\x01\x03'
        await adapter._process_buffer()

        assert len(received_events) == 2
        assert received_events[0].key == "A"
        assert "CTRL" in received_events[0].modifiers
        assert received_events[1].key == "C"
        assert "CTRL" in received_events[1].modifiers


# ============================================================================
# Factory Tests
# ============================================================================

class TestKeyboardFactoryReal:
    """Test real keyboard adapter factory with mocking"""

    @pytest.mark.asyncio
    async def test_factory_tries_adapters_in_order(self):
        """Factory should try evdev, then stdin, then dummy in order"""
        event_bus = EventBus()
        call_order = []

        # Mock all adapters to track call order
        original_evdev_run = EvdevKeyboardAdapter.run
        original_stdin_run = StdinKeyboardAdapter.run
        original_dummy_run = DummyKeyboardAdapter.run

        async def track_evdev(self):
            call_order.append('evdev')
            raise RuntimeError("Evdev not available")

        async def track_stdin(self):
            call_order.append('stdin')
            raise RuntimeError("STDIN not available")

        async def track_dummy(self):
            call_order.append('dummy')
            # Block until cancelled
            await asyncio.sleep(10)

        with patch.object(EvdevKeyboardAdapter, 'run', track_evdev), \
             patch.object(StdinKeyboardAdapter, 'run', track_stdin), \
             patch.object(DummyKeyboardAdapter, 'run', track_dummy):

            task = asyncio.create_task(start_keyboard(event_bus))
            await asyncio.sleep(0.2)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        assert call_order == ['evdev', 'stdin', 'dummy']

    @pytest.mark.asyncio
    async def test_factory_stops_at_first_working_adapter(self):
        """Factory should stop trying once an adapter works"""
        event_bus = EventBus()
        call_order = []

        async def track_evdev(self):
            call_order.append('evdev')
            # This one works - blocks until cancelled
            await asyncio.sleep(10)

        async def track_stdin(self):
            call_order.append('stdin')
            await asyncio.sleep(10)

        with patch.object(EvdevKeyboardAdapter, 'run', track_evdev), \
             patch.object(StdinKeyboardAdapter, 'run', track_stdin):

            task = asyncio.create_task(start_keyboard(event_bus))
            await asyncio.sleep(0.2)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        # Should only try evdev, not stdin
        assert call_order == ['evdev']

    @pytest.mark.asyncio
    async def test_factory_with_evdev_construction_failure(self):
        """Factory should handle adapter construction failures gracefully"""
        event_bus = EventBus()
        call_order = []

        # Mock evdev import to fail
        with patch('hardware.input.keyboard.factory.EvdevKeyboardAdapter', side_effect=ImportError("evdev not installed")):

            async def track_stdin(self):
                call_order.append('stdin')
                raise RuntimeError("STDIN not a TTY")

            async def track_dummy(self):
                call_order.append('dummy')
                await asyncio.sleep(10)

            with patch.object(StdinKeyboardAdapter, 'run', track_stdin), \
                 patch.object(DummyKeyboardAdapter, 'run', track_dummy):

                task = asyncio.create_task(start_keyboard(event_bus))
                await asyncio.sleep(0.2)
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Should skip evdev (construction failed) and try stdin, then dummy
        assert call_order == ['stdin', 'dummy']


# ============================================================================
# Integration Tests
# ============================================================================

class TestKeyboardSystemIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_event_flow_through_real_eventbus(self):
        """Test that events flow correctly through real EventBus"""
        event_bus = EventBus()
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler)

        # Manually publish event (simulating adapter behavior)
        await event_bus.publish(
            KeyboardKeyPressEvent("A", modifiers=["CTRL"])
        )

        assert len(received_events) == 1
        assert received_events[0].key == "A"
        assert received_events[0].modifiers == ["CTRL"]

    @pytest.mark.asyncio
    async def test_multiple_handlers_receive_events(self):
        """Test that multiple handlers all receive keyboard events"""
        event_bus = EventBus()
        handler1_events = []
        handler2_events = []

        async def handler1(event):
            handler1_events.append(event)

        async def handler2(event):
            handler2_events.append(event)

        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler1)
        event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, handler2)

        await event_bus.publish(KeyboardKeyPressEvent("B"))

        assert len(handler1_events) == 1
        assert len(handler2_events) == 1
        assert handler1_events[0].key == "B"
        assert handler2_events[0].key == "B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
