"""
Unit tests for Color class
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Color, ColorMode
from managers.color_manager import ColorManager


def test_color_from_hue():
    """Test creating Color from HUE"""
    print('✓ test_color_from_hue')

    c = Color.from_hue(120)

    assert c.mode == ColorMode.HUE
    assert c.to_hue() == 120
    assert c.to_rgb() == (0, 255, 0)  # Green at 120°

    print(f'  HUE=120° → RGB={c.to_rgb()} (green)')


def test_color_from_preset():
    """Test creating Color from PRESET"""
    print('✓ test_color_from_preset')

    cm = ColorManager()
    c = Color.from_preset("warm_white", cm)

    assert c.mode == ColorMode.PRESET
    assert c.to_rgb() == (255, 200, 150)  # Warm white RGB

    print(f'  PRESET=warm_white → RGB={c.to_rgb()}')


def test_color_from_rgb():
    """Test creating Color from RGB"""
    print('✓ test_color_from_rgb')

    c = Color.from_rgb(255, 0, 0)

    assert c.mode == ColorMode.RGB
    assert c.to_rgb() == (255, 0, 0)  # Red

    print(f'  RGB=(255, 0, 0) → RGB={c.to_rgb()} (red)')


def test_color_adjust_hue():
    """Test adjusting HUE"""
    print('✓ test_color_adjust_hue')

    c1 = Color.from_hue(120)
    c2 = c1.adjust_hue(30)

    assert c2.mode == ColorMode.HUE
    assert c2.to_hue() == 150
    assert c1.to_hue() == 120  # Original unchanged

    print(f'  120° + 30° = 150°')
    print(f'  RGB: {c1.to_rgb()} → {c2.to_rgb()}')


def test_color_adjust_hue_wrap():
    """Test HUE wrapping at 360°"""
    print('✓ test_color_adjust_hue_wrap')

    c1 = Color.from_hue(350)
    c2 = c1.adjust_hue(20)  # Should wrap to 10°

    assert c2.to_hue() == 10

    print(f'  350° + 20° = 10° (wrapped)')


def test_color_next_preset():
    """Test cycling through presets"""
    print('✓ test_color_next_preset')

    cm = ColorManager()

    c1 = Color.from_preset("red", cm)
    c2 = c1.next_preset(1, cm)  # Should be orange

    assert c2.mode == ColorMode.PRESET
    # Get preset index to verify cycling
    order = cm.preset_order
    assert order.index("red") == 0
    assert order.index("orange") == 1

    print(f'  red → orange')
    print(f'  RGB: {c1.to_rgb()} → {c2.to_rgb()}')


def test_color_mode_conversion_hue_to_preset():
    """Test converting HUE mode to PRESET mode"""
    print('✓ test_color_mode_conversion_hue_to_preset')

    cm = ColorManager()

    # Red hue (0°) should map to "red" preset
    c1 = Color.from_hue(0)
    c2 = c1.to_preset_mode(cm)

    assert c2.mode == ColorMode.PRESET
    # Find closest preset to RGB(255, 0, 0)
    closest = c2._preset_name  # Should be "red"

    print(f'  HUE=0° → PRESET={closest}')
    print(f'  RGB: {c1.to_rgb()} → {c2.to_rgb()}')


def test_color_mode_conversion_preset_to_hue():
    """Test converting PRESET mode to HUE mode"""
    print('✓ test_color_mode_conversion_preset_to_hue')

    cm = ColorManager()

    c1 = Color.from_preset("red", cm)
    c2 = c1.to_hue_mode()

    assert c2.mode == ColorMode.HUE
    # Red preset (255, 0, 0) converts to hue 0°
    assert c2.to_hue() == 0

    print(f'  PRESET=red → HUE={c2.to_hue()}°')
    print(f'  RGB: {c1.to_rgb()} → {c2.to_rgb()}')


def test_color_serialization():
    """Test Color serialization and deserialization"""
    print('✓ test_color_serialization')

    cm = ColorManager()

    # Test HUE mode
    c1 = Color.from_hue(240)
    data1 = c1.to_dict()
    c1_restored = Color.from_dict(data1, cm)

    assert c1_restored.mode == ColorMode.HUE
    assert c1_restored.to_hue() == 240
    assert c1.to_rgb() == c1_restored.to_rgb()

    print(f'  HUE mode: {data1}')

    # Test PRESET mode
    c2 = Color.from_preset("warm_white", cm)
    data2 = c2.to_dict()
    c2_restored = Color.from_dict(data2, cm)

    assert c2_restored.mode == ColorMode.PRESET
    assert c2.to_rgb() == c2_restored.to_rgb()

    print(f'  PRESET mode: {data2}')

    # Test RGB mode
    c3 = Color.from_rgb(100, 150, 200)
    data3 = c3.to_dict()
    c3_restored = Color.from_dict(data3, cm)

    assert c3_restored.mode == ColorMode.RGB
    assert c3.to_rgb() == c3_restored.to_rgb()

    print(f'  RGB mode: {data3}')


def test_white_preset_preservation():
    """Test that white presets preserve exact RGB values"""
    print('✓ test_white_preset_preservation')

    cm = ColorManager()

    # White presets should cache RGB to preserve exact color
    whites = ['white', 'warm_white', 'cool_white']

    for preset_name in whites:
        c = Color.from_preset(preset_name, cm)
        expected_rgb = cm.get_preset_rgb(preset_name)

        assert c.to_rgb() == expected_rgb

        print(f'  {preset_name}: {c.to_rgb()} (preserved)')


def test_color_string_representation():
    """Test Color __str__ method"""
    print('✓ test_color_string_representation')

    cm = ColorManager()

    c1 = Color.from_hue(120)
    assert "HUE=120°" in str(c1)

    c2 = Color.from_preset("red", cm)
    assert "PRESET=red" in str(c2)

    c3 = Color.from_rgb(255, 100, 50)
    assert "RGB=(255, 100, 50)" in str(c3)

    print(f'  HUE: {c1}')
    print(f'  PRESET: {c2}')
    print(f'  RGB: {c3}')


def run_all_tests():
    """Run all color tests"""
    print('=' * 60)
    print('Color Class Tests')
    print('=' * 60)
    print()

    test_color_from_hue()
    print()
    test_color_from_preset()
    print()
    test_color_from_rgb()
    print()
    test_color_adjust_hue()
    print()
    test_color_adjust_hue_wrap()
    print()
    test_color_next_preset()
    print()
    test_color_mode_conversion_hue_to_preset()
    print()
    test_color_mode_conversion_preset_to_hue()
    print()
    test_color_serialization()
    print()
    test_white_preset_preservation()
    print()
    test_color_string_representation()

    print()
    print('=' * 60)
    print('✓ All tests passed!')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
