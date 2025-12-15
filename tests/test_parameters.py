"""
Unit tests for Parameter system
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import load_parameters, ParamID, ParameterType


def test_load_parameters():
    """Test loading parameters from config.yaml"""
    params = load_parameters()

    print('✓ test_load_parameters')
    print(f'  Loaded {len(params)} parameters')

    # Check all expected parameters exist
    expected = [
        ParamID.ANIM_SPEED,
        ParamID.ANIM_PRIMARY_COLOR_HUE,
        ParamID.ANIM_INTENSITY,
        ParamID.ANIM_SECONDARY_COLOR_HUE,
        ParamID.ANIM_TERTIARY_COLOR_HUE,
        ParamID.ANIM_LENGTH,
        ParamID.ANIM_HUE_OFFSET,
    ]

    for param_id in expected:
        assert param_id in params, f"Missing parameter: {param_id.name}"

    print(f'  All {len(expected)} expected parameters present')


def test_parameter_types():
    """Test parameter types are correct"""
    params = load_parameters()

    print('✓ test_parameter_types')

    # Animation base parameters
    assert params[ParamID.ANIM_SPEED].type == ParameterType.PERCENTAGE
    assert params[ParamID.ANIM_PRIMARY_COLOR_HUE].type == ParameterType.COLOR

    # Additional animation parameters
    assert params[ParamID.ANIM_INTENSITY].type == ParameterType.PERCENTAGE
    assert params[ParamID.ANIM_LENGTH].type == ParameterType.RANGE_CUSTOM
    assert params[ParamID.ANIM_HUE_OFFSET].type == ParameterType.RANGE_CUSTOM

    print('  All parameter types correct')


def test_percentage_parameter():
    """Test PERCENTAGE parameter (brightness)"""
    params = load_parameters()
    # brightness = params[ParamID.ZONE_BRIGHTNESS]

    print('✓ test_percentage_parameter')

    # Test defaults
    assert brightness.default == 100
    assert brightness.min_val == 0
    assert brightness.max_val == 100
    assert brightness.step == 5
    assert brightness.wraps == False
    assert brightness.unit == "%"

    # Test adjustment
    assert brightness.adjust(50, 2) == 60  # +2 steps of 5 = +10
    assert brightness.adjust(50, -3) == 35  # -3 steps of 5 = -15

    # Test clamping
    assert brightness.clamp(110) == 100  # Clamp to max
    assert brightness.clamp(-10) == 0   # Clamp to min

    # Test formatting
    assert brightness.format_value(50) == "50%"
    assert brightness.format_value(100) == "100%"

    print('  Adjustment: 50 + 2 steps = 60')
    print('  Clamp: 110 → 100 (max)')
    print('  Format: 50 → "50%"')


def test_range_custom_parameter():
    """Test RANGE_CUSTOM parameter (length)"""
    params = load_parameters()
    length = params[ParamID.ANIM_LENGTH]

    print('✓ test_range_custom_parameter')

    # Test defaults
    assert length.default == 5
    assert length.min_val == 2
    assert length.max_val == 20
    assert length.step == 1
    assert length.unit == "px"

    # Test adjustment
    assert length.adjust(5, 3) == 8    # +3 steps
    assert length.adjust(5, -10) == 2  # Clamped to min
    assert length.adjust(15, 10) == 20 # Clamped to max

    # Test formatting
    assert length.format_value(5) == "5px"

    print('  Adjustment: 5 + 3 steps = 8')
    print('  Clamp: 5 - 10 steps → 2 (min)')
    print('  Format: 5 → "5px"')


def test_boolean_parameter():
    """Test BOOLEAN parameter (zone_reversed)"""
    params = load_parameters()
    reversed_param = params[ParamID.ZONE_REVERSED]

    print('✓ test_boolean_parameter')

    # Test defaults
    assert reversed_param.default == False
    assert reversed_param.type == ParameterType.BOOLEAN

    # Test validation
    assert reversed_param.validate(True) == True
    assert reversed_param.validate(False) == True
    assert reversed_param.validate(42) == False
    assert reversed_param.validate("true") == False

    # Test formatting
    assert reversed_param.format_value(True) == "ON"
    assert reversed_param.format_value(False) == "OFF"

    print('  Validate: True/False ✓, 42 ✗')
    print('  Format: True → "ON", False → "OFF"')


def test_color_parameter():
    """Test COLOR parameter"""
    params = load_parameters()
    zone_color = params[ParamID.ZONE_COLOR]

    print('✓ test_color_parameter')

    # Test defaults
    assert zone_color.type == ParameterType.COLOR
    assert zone_color.default == 0
    assert zone_color.color_modes == ["HUE", "PRESET"]

    # COLOR parameters don't use min/max/step (handled by Color class)
    assert zone_color.min_val is None
    assert zone_color.max_val is None

    print('  Type: COLOR')
    print('  Modes: HUE, PRESET')
    print('  Default: 0')


def run_all_tests():
    """Run all parameter tests"""
    print('=' * 60)
    print('Parameter System Tests')
    print('=' * 60)
    print()

    test_load_parameters()
    print()
    test_parameter_types()
    print()
    test_percentage_parameter()
    print()
    test_range_custom_parameter()
    print()
    test_boolean_parameter()
    print()
    test_color_parameter()

    print()
    print('=' * 60)
    print('✓ All tests passed!')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
