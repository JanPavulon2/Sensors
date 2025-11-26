"""
Master test runner - runs all unit tests
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
from tests import test_parameters, test_color_manager, test_color


def main():
    """Run all test suites"""
    print('\n')
    print('╔' + '═' * 58 + '╗')
    print('║' + ' ' * 58 + '║')
    print('║' + '  LED Control Station - Unit Tests'.center(58) + '║')
    print('║' + ' ' * 58 + '║')
    print('╚' + '═' * 58 + '╝')
    print('\n')

    failed = False

    # Run all test suites
    test_suites = [
        ('Parameters', test_parameters.run_all_tests),
        ('ColorManager', test_color_manager.run_all_tests),
        ('Color', test_color.run_all_tests),
    ]

    for name, test_func in test_suites:
        try:
            test_func()
            print()
        except Exception as e:
            print(f'\n✗ {name} tests FAILED: {e}\n')
            failed = True

    # Final summary
    print('\n')
    print('╔' + '═' * 58 + '╗')
    print('║' + ' ' * 58 + '║')
    if failed:
        print('║' + '  ✗ SOME TESTS FAILED'.center(58) + '║')
    else:
        print('║' + '  ✓ ALL TESTS PASSED'.center(58) + '║')
    print('║' + ' ' * 58 + '║')
    print('╚' + '═' * 58 + '╝')
    print('\n')

    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
