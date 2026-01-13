#!/usr/bin/env python3
"""
Test that logger is a true singleton and retains broadcaster after configure_logger().
"""

import sys
from pathlib import Path

# UTF-8 encoding setup
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.logger import get_logger, configure_logger
from models.enums import LogLevel, LogCategory

# Test 1: Logger should be singleton
print("Test 1: Logger singleton identity")
logger1 = get_logger()
logger2 = get_logger()
assert logger1 is logger2, "Logger is not a singleton!"
print("✓ Logger is a singleton")

# Test 2: configure_logger() should NOT create new instance
print("\nTest 2: configure_logger() preserves singleton")
original_logger = get_logger()
configure_logger(LogLevel.DEBUG)
after_config_logger = get_logger()
assert original_logger is after_config_logger, "configure_logger() created a new instance!"
print("✓ configure_logger() preserves singleton")

# Test 3: Logger should have correct properties after configuration
print("\nTest 3: Logger properties after configuration")
assert get_logger().min_level == LogLevel.DEBUG, "min_level not set correctly"
print(f"✓ Logger min_level is correctly set to {LogLevel.DEBUG}")

# Test 4: Check broadcaster can be set on singleton
print("\nTest 4: Broadcaster setting (simulation)")
class MockBroadcaster:
    def log(self, **kwargs):
        pass

mock_broadcaster = MockBroadcaster()
get_logger().set_broadcaster(mock_broadcaster)
assert get_logger()._broadcaster is mock_broadcaster, "Broadcaster not set!"
print("✓ Broadcaster can be set on singleton")

print("\n✅ All singleton tests passed!")
