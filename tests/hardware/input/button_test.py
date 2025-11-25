import pytest
from unittest.mock import patch, MagicMock
from hardware import Button


@pytest.fixture
def gpio_mock():
    """Mock RPi.GPIO module."""
    with patch("hardware.input.button.GPIO") as mock_gpio:
        mock_gpio.HIGH = 1
        mock_gpio.LOW = 0
        yield mock_gpio


@pytest.fixture
def time_mock():
    """Mock time.time."""
    with patch("hardware.input.button.time") as mock_time:
        mock_time.time.return_value = 1000.0
        yield mock_time


def test_initial_state_reads_gpio(gpio_mock, time_mock):
    gpio_mock.input.return_value = gpio_mock.LOW
    btn = Button(pin=5, debounce_time=0.3)

    assert btn._last_state == gpio_mock.LOW


def test_falling_edge_detection(gpio_mock, time_mock):
    gpio_mock.input.side_effect = [
        1,  # constructor reads initial state
        1,  # 1st is_pressed() -> no falling edge
        0,  # 2nd is_pressed() -> falling edge detected
    ]
    btn = Button(pin=5, debounce_time=0.3)

    assert btn.is_pressed() is False  # still HIGH
    assert btn.is_pressed() is True   # falling edge detected


def test_debounce_prevents_second_press(gpio_mock, time_mock):
    gpio_mock.input.side_effect = [1, 0, 1, 0]

    btn = Button(pin=5, debounce_time=0.3)

    assert btn.is_pressed() is True   # first press ok

    # Not enough time passed → no press
    time_mock.time.return_value += 0.1
    assert btn.is_pressed() is False


def test_press_after_debounce(gpio_mock, time_mock):
    gpio_mock.input.side_effect = [
        1,  # constructor
        0,  # first press
        1,  # released
        0,  # second press
    ]

    btn = Button(pin=5, debounce_time=0.3)

    assert btn.is_pressed() is True  # first falling edge detected

    time_mock.time.return_value += 0.5

    assert btn.is_pressed() is False  # reading "1" (release)
    assert btn.is_pressed() is True   # second falling edge detected

def test_reset(gpio_mock, time_mock):
    gpio_mock.input.return_value = 0
    btn = Button(pin=5)
    btn._last_state = True
    btn._last_press_time = 999

    btn.reset()

    assert btn._last_state == 0
    assert btn._last_press_time == 0.0


def test_is_held(gpio_mock):
    gpio_mock.input.return_value = 0
    btn = Button(pin=5)
    assert btn.is_held() is True

    gpio_mock.input.return_value = 1
    assert btn.is_held() is False