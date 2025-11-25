import RPi.GPIO as GPIO
import time

# --- KONFIGURACJA ---
BUZZER_PIN = 12  # możesz zmienić, np. na 12, 13, 19 itp.

# Initialize GPIO ONCE at module load time
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


class Buzzer:
    """
    Hardware buzzer with optional PWM mode.

    Args:
        pin (int): BCM GPIO pin number
        active (bool): True = active buzzer (ON/OFF), False = passive buzzer (PWM)
        initial_freq (int): default frequency for passive mode (Hz)
        duty_cycle (float): default duty cycle for PWM (0-100)
    """

    def __init__(
        self,
        pin: int,
        active: bool = True,
        initial_freq: int = 2200,
        duty_cycle: float = 50.0,
    ):
        self.pin = pin
        self.active = active
        self.initial_freq = initial_freq
        self.duty_cycle = duty_cycle

        self._pwm = None

        # Setup pin as output (CRITICAL for both active and passive buzzers)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)

        if not active:
            # Create PWM object AFTER pin is configured
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
        # if self.active:
        #     raise RuntimeError("Active buzzer cannot play tones. Use beep().")

        if not self._pwm:
            return
        
        if not self._pwm_started:
            self._pwm.start(40)
            self._pwm_started = True

        self._pwm.ChangeFrequency(freq)
        time.sleep(duration)
        self._pwm.stop()
        self._pwm_started = False

    def stop(self):
        """Stop passive buzzer PWM if running."""
        if self._pwm_started and self._pwm is not None:
            self._pwm.stop()
            self._pwm_started = False
            
            

# --- PWM 50 Hz ---
#pwm = GPIO.PWM(BUZZER_PIN, 50)
#pwm.start(7.5)

try:
    while True:
        print("Biip: ")
        bz = Buzzer(pin=19, active=True)
        bz.beep(0.1)

        #bz = Buzzer(pin=12, active=False)
        bz.play_tone(2000, 0.3)
        
        # set_speed(-1.0)
        # time.sleep(2)

        # print("STOP")
        # set_speed(0.0)
        # time.sleep(1)

        # print("Pelna w lewo")
        # set_speed(-1.0)
        # time.sleep(2)

        # print("STOP")
        # set_speed(0.0)
        time.sleep(2)

except KeyboardInterrupt:
    pass
finally:
    # pwm.stop()
    GPIO.cleanup()
    