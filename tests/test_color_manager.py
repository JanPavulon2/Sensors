"""
Unit tests for ColorManager
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from managers.color_manager import ColorManager


def test_load_colors():
    """Test loading colors from colors.yaml"""
    print('✓ test_load_colors')

    cm = ColorManager()

    # Check we loaded colors
    assert len(cm.preset_colors) > 0
    assert len(cm.preset_order) > 0

    print(f'  Loaded {len(cm.preset_colors)} preset colors')
    print(f'  Preset order: {len(cm.preset_order)} colors')


def test_preset_colors_structure():
    """Test preset colors have correct structure"""
    print('✓ test_preset_colors_structure')

    cm = ColorManager()

    # Check basic colors exist
    basic_colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
    for color in basic_colors:
        assert color in cm.preset_colors, f"Missing basic color: {color}"
        rgb = cm.preset_colors[color]
        assert len(rgb) == 3, f"Invalid RGB for {color}"
        assert all(0 <= v <= 255 for v in rgb), f"RGB values out of range for {color}"

    print(f'  All basic colors present with valid RGB')


def test_white_presets():
    """Test white preset detection"""
    print('✓ test_white_presets')

    cm = ColorManager()

    # Check white presets are identified
    expected_whites = {'white', 'warm_white', 'cool_white'}
    assert cm.white_presets == expected_whites

    # Check white detection method
    assert cm.is_white_preset('white') == True
    assert cm.is_white_preset('warm_white') == True
    assert cm.is_white_preset('cool_white') == True
    assert cm.is_white_preset('red') == False
    assert cm.is_white_preset('blue') == False

    print(f'  White presets: {cm.white_presets}')


def test_get_preset_rgb():
    """Test getting RGB values for presets"""
    print('✓ test_get_preset_rgb')

    cm = ColorManager()

    # Test known colors
    red = cm.get_preset_rgb('red')
    assert red == (255, 0, 0)

    warm_white = cm.get_preset_rgb('warm_white')
    assert warm_white == (255, 200, 150)

    # Test unknown color raises error
    try:
        cm.get_preset_rgb('nonexistent_color')
        assert False, "Should have raised KeyError"
    except KeyError:
        pass

    print(f'  red: {red}')
    print(f'  warm_white: {warm_white}')


def test_get_preset_by_index():
    """Test getting preset by cycling index"""
    print('✓ test_get_preset_by_index')

    cm = ColorManager()

    # Test forward cycling
    name0, rgb0 = cm.get_preset_by_index(0)
    name1, rgb1 = cm.get_preset_by_index(1)
    name2, rgb2 = cm.get_preset_by_index(2)

    assert name0 == cm.preset_order[0]
    assert name1 == cm.preset_order[1]
    assert name2 == cm.preset_order[2]

    print(f'  Index 0: {name0} {rgb0}')
    print(f'  Index 1: {name1} {rgb1}')
    print(f'  Index 2: {name2} {rgb2}')

    # Test wrapping
    last_index = len(cm.preset_order) - 1
    name_last, _ = cm.get_preset_by_index(last_index)
    name_wrap, _ = cm.get_preset_by_index(last_index + 1)  # Should wrap to 0

    assert name_wrap == cm.preset_order[0]

    print(f'  Last index ({last_index}): {name_last}')
    print(f'  Wrapped index ({last_index + 1}): {name_wrap}')


def test_preset_order_consistency():
    """Test preset_order matches preset_colors"""
    print('✓ test_preset_order_consistency')

    cm = ColorManager()

    # All colors in preset_order should exist in preset_colors
    for preset_name in cm.preset_order:
        assert preset_name in cm.preset_colors, f"preset_order contains unknown color: {preset_name}"

    print(f'  All {len(cm.preset_order)} colors in order are valid')


def test_color_categories():
    """Test colors have correct categories (from YAML)"""
    print('✓ test_color_categories')

    cm = ColorManager()

    # Load raw YAML to check categories
    import yaml
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent / "src/config/colors.yaml"
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    # Check white category
    white_category_colors = [
        name for name, info in data['presets'].items()
        if info.get('category') == 'white'
    ]

    assert set(white_category_colors) == cm.white_presets

    print(f'  White category colors: {white_category_colors}')
    print(f'  Matches white_presets: {cm.white_presets}')


def run_all_tests():
    """Run all ColorManager tests"""
    print('=' * 60)
    print('ColorManager Tests')
    print('=' * 60)
    print()

    test_load_colors()
    print()
    test_preset_colors_structure()
    print()
    test_white_presets()
    print()
    test_get_preset_rgb()
    print()
    test_get_preset_by_index()
    print()
    test_preset_order_consistency()
    print()
    test_color_categories()

    print()
    print('=' * 60)
    print('✓ All tests passed!')
    print('=' * 60)


if __name__ == '__main__':
    run_all_tests()
