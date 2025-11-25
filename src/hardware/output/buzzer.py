"""
Buzzer Component - Hardware Abstraction Layer (Layer 1)

Supports:
- Active buzzers (simple ON/OFF beeping)
- Passive buzzers (PWM frequency control for melodies)
"""

import time
import RPi.GPIO as GPIO


class Buzzer:
    """
    Hardware buzzer abstraction supporting both active and passive types.

    ACTIVE BUZZER (active=True):
    - Simple ON/OFF control via GPIO.output()
    - Produces a fixed-frequency tone (beeping sound)
    - Use beep() to create alert sounds
    - Does NOT support play_tone() with variable frequencies

    PASSIVE BUZZER (active=False):
    - Requires PWM signal for sound generation
    - play_tone(freq) can produce different pitches (melodies)
    - beep() uses the initial_freq for the default tone

    Args:
        pin (int): BCM GPIO pin number
        active (bool): True = active buzzer, False = passive buzzer (PWM)
        initial_freq (int): default frequency for passive mode (Hz, default 1000)
        duty_cycle (float): PWM duty cycle for passive mode (0-100, default 50)
    """

    def __init__(
        self,
        pin: int,
        active: bool = True,
        initial_freq: int = 1000,
        duty_cycle: float = 50.0,
    ):
        self.pin = pin
        self.active = active
        self.initial_freq = initial_freq
        self.duty_cycle = duty_cycle

        self._pwm = None
        self._pwm_started = False

        # For passive buzzers, create PWM object
        if not active:
            self._pwm = GPIO.PWM(self.pin, self.initial_freq)
            self._pwm_started = False

    # ----------------------------------------------------------------------
    # ACTIVE BUZZER METHODS (digital on/off)
    # ----------------------------------------------------------------------

    def on(self):
        """Turn ON an active buzzer."""
        if self.active:
            GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        """Turn OFF an active buzzer."""
        if self.active:
            GPIO.output(self.pin, GPIO.LOW)

    # ----------------------------------------------------------------------
    # PASSIVE BUZZER (PWM) METHODS
    # ----------------------------------------------------------------------

    def beep(self, duration: float = 0.1):
        """
        Beep either active or passive buzzer for given duration.
        """
        if self.active:
            self.on()
            time.sleep(duration)
            self.off()
        else:
            self.play_tone(self.initial_freq, duration)

    def play_tone(self, freq: int, duration: float):
        """
        Play tone (passive buzzer only).

        Args:
            freq: frequency in Hz
            duration: tone duration in seconds
        """
        if self.active:
            raise RuntimeError("Active buzzer cannot play tones. Use beep().")

        if not self._pwm_started:
            self._pwm.start(self.duty_cycle)
            self._pwm_started = True

        self._pwm.ChangeFrequency(freq)
        time.sleep(duration)
        self._pwm.stop()
        self._pwm_started = False

    def stop(self):
        """Stop passive buzzer PWM if running."""
        if self._pwm_started:
            self._pwm.stop()
            self._pwm_started = False