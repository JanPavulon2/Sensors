#!/usr/bin/env python3
"""
Test script for event bus functionality

Tests event creation, publishing, subscription, middleware, and filtering.
"""

import asyncio
import sys
from pathlib import Path

# Set UTF-8 encoding for output
if sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent, EventType
from models.enums import EncoderSource, ButtonID
from services.event_bus import EventBus


async def test_basic_pub_sub():
    """Test basic publish/subscribe"""
    print("Test 1: Basic pub/sub...")
    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(EventType.ENCODER_ROTATE, handler)
    await bus.publish(EncoderRotateEvent(EncoderSource.SELECTOR, 1))

    assert len(received) == 1
    assert received[0].delta == 1
    print("✓ Basic pub/sub works!")


async def test_filtering():
    """Test per-handler filtering"""
    print("\nTest 2: Event filtering...")
    bus = EventBus()
    selector_events = []
    modulator_events = []

    async def selector_handler(event):
        selector_events.append(event)

    async def modulator_handler(event):
        modulator_events.append(event)

    # Subscribe with filters
    bus.subscribe(
        EventType.ENCODER_ROTATE,
        selector_handler,
        filter_fn=lambda e: e.source == EncoderSource.SELECTOR
    )
    bus.subscribe(
        EventType.ENCODER_ROTATE,
        modulator_handler,
        filter_fn=lambda e: e.source == EncoderSource.MODULATOR
    )

    # Publish events
    await bus.publish(EncoderRotateEvent(EncoderSource.SELECTOR, 1))
    await bus.publish(EncoderRotateEvent(EncoderSource.MODULATOR, -1))
    await bus.publish(EncoderRotateEvent(EncoderSource.SELECTOR, 1))

    assert len(selector_events) == 2
    assert len(modulator_events) == 1
    print("✓ Filtering works!")


async def test_middleware():
    """Test middleware blocking"""
    print("\nTest 3: Middleware blocking...")
    bus = EventBus()
    received = []

    # Middleware that blocks all modulator events
    def block_modulator(event):
        if event.source == EncoderSource.MODULATOR:
            return None  # Block
        return event

    bus.add_middleware(block_modulator)

    async def handler(event):
        received.append(event)

    bus.subscribe(EventType.ENCODER_ROTATE, handler)

    # Publish events
    await bus.publish(EncoderRotateEvent(EncoderSource.SELECTOR, 1))
    await bus.publish(EncoderRotateEvent(EncoderSource.MODULATOR, 1))  # Should be blocked

    assert len(received) == 1  # Only selector event received
    assert received[0].source == EncoderSource.SELECTOR
    print("✓ Middleware blocking works!")


async def test_priority():
    """Test priority-based handler execution"""
    print("\nTest 4: Priority execution...")
    bus = EventBus()
    execution_order = []

    async def low_priority_handler(event):
        execution_order.append("low")

    async def high_priority_handler(event):
        execution_order.append("high")

    async def medium_priority_handler(event):
        execution_order.append("medium")

    # Subscribe with different priorities
    bus.subscribe(EventType.ENCODER_ROTATE, low_priority_handler, priority=0)
    bus.subscribe(EventType.ENCODER_ROTATE, high_priority_handler, priority=100)
    bus.subscribe(EventType.ENCODER_ROTATE, medium_priority_handler, priority=50)

    await bus.publish(EncoderRotateEvent(EncoderSource.SELECTOR, 1))

    assert execution_order == ["high", "medium", "low"]
    print("✓ Priority execution works!")


async def test_button_events():
    """Test button press events"""
    print("\nTest 5: Button events...")
    bus = EventBus()
    button_presses = []

    async def button_handler(event):
        button_presses.append(event.source)

    bus.subscribe(EventType.BUTTON_PRESS, button_handler)

    # Simulate button presses
    await bus.publish(ButtonPressEvent(ButtonID.BTN1))
    await bus.publish(ButtonPressEvent(ButtonID.BTN2))
    await bus.publish(ButtonPressEvent(ButtonID.BTN3))

    assert button_presses == [ButtonID.BTN1, ButtonID.BTN2, ButtonID.BTN3]
    print("✓ Button events work!")


async def test_encoder_click():
    """Test encoder click events"""
    print("\nTest 6: Encoder click events...")
    bus = EventBus()
    clicks = []

    async def click_handler(event):
        clicks.append(event.source)

    bus.subscribe(EventType.ENCODER_CLICK, click_handler)

    await bus.publish(EncoderClickEvent(EncoderSource.SELECTOR))
    await bus.publish(EncoderClickEvent(EncoderSource.MODULATOR))

    assert clicks == [EncoderSource.SELECTOR, EncoderSource.MODULATOR]
    print("✓ Encoder click events work!")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Event Bus Test Suite")
    print("=" * 60)

    try:
        await test_basic_pub_sub()
        await test_filtering()
        await test_middleware()
        await test_priority()
        await test_button_events()
        await test_encoder_click()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
