"""GPIO Controller for Raspberry Pi 5 relay control."""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import gpiod, but allow fallback for development/testing
try:
    import gpiod
    from gpiod.line import Direction, Value
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("gpiod not available - running in simulation mode")


class GPIOController:
    """
    Controls GPIO pins for relay operation on Raspberry Pi 5.
    
    Uses the modern gpiod library which is compatible with Pi 5's RP1 chip.
    Falls back to simulation mode when not running on a Pi.
    """

    def __init__(
        self,
        chip_path: str = "/dev/gpiochip4",
        pin: int = 17,
        active_high: bool = True,
        pulse_duration_ms: int = 500,
        door_sensor_pin: int = 27
    ):
        """
        Initialize the GPIO controller.

        Args:
            chip_path: Path to the GPIO chip device (Pi 5 uses gpiochip4)
            pin: GPIO pin number for the relay
            active_high: True if relay activates on HIGH signal
            pulse_duration_ms: Duration of relay pulse in milliseconds
            door_sensor_pin: GPIO pin number for the door reed sensor
        """
        self.chip_path = chip_path
        self.pin = pin
        self.active_high = active_high
        self.pulse_duration_ms = pulse_duration_ms
        self.door_sensor_pin = door_sensor_pin
        self._request: Optional[object] = None
        self._sensor_request: Optional[object] = None
        self._simulation_mode = not GPIO_AVAILABLE
        self._simulation_door_state = False  # False = CLOSED in simulation

        if self._simulation_mode:
            logger.info("GPIO Controller running in SIMULATION mode")
        else:
            logger.info(f"GPIO Controller initialized: chip={chip_path}, pin={pin}, active_high={active_high}, door_sensor_pin={door_sensor_pin}")

    def _get_on_value(self) -> 'Value':
        """Get the gpiod Value for turning relay ON."""
        return Value.ACTIVE if self.active_high else Value.INACTIVE

    def _get_off_value(self) -> 'Value':
        """Get the gpiod Value for turning relay OFF."""
        return Value.INACTIVE if self.active_high else Value.ACTIVE

    def _ensure_request(self) -> bool:
        """
        Ensure we have an active GPIO line request.
        
        Returns:
            True if request is available, False otherwise
        """
        if self._simulation_mode:
            return True

        if self._request is None:
            try:
                self._request = gpiod.request_lines(
                    self.chip_path,
                    consumer="garagepi",
                    config={
                        self.pin: gpiod.LineSettings(
                            direction=Direction.OUTPUT,
                            output_value=self._get_off_value()
                        )
                    }
                )
                logger.info(f"GPIO line {self.pin} requested successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to request GPIO line: {e}")
                return False
        return True

    def _ensure_sensor_request(self) -> bool:
        """
        Ensure we have an active GPIO line request for the door sensor.
        
        Returns:
            True if request is available, False otherwise
        """
        if self._simulation_mode:
            return True

        if self._sensor_request is None:
            try:
                self._sensor_request = gpiod.request_lines(
                    self.chip_path,
                    consumer="garagepi-sensor",
                    config={
                        self.door_sensor_pin: gpiod.LineSettings(
                            direction=Direction.INPUT
                        )
                    }
                )
                logger.info(f"GPIO line {self.door_sensor_pin} (sensor) requested successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to request sensor GPIO line: {e}")
                return False
        return True

    def read_door_sensor(self) -> str:
        """
        Read the door sensor state.
        
        Returns:
            "CLOSED" if door is closed (sensor LOW), "OPEN" if door is open (sensor HIGH),
            or "UNKNOWN" if reading fails
        """
        if self._simulation_mode:
            state = "CLOSED" if not self._simulation_door_state else "OPEN"
            logger.debug(f"[SIMULATION] Door sensor state: {state}")
            return state

        if not self._ensure_sensor_request():
            return "UNKNOWN"

        try:
            value = self._sensor_request.get_value(self.door_sensor_pin)
            # Reed sensor: LOW (INACTIVE) = magnet present = door CLOSED
            # HIGH (ACTIVE) = magnet away = door OPEN
            if value == Value.INACTIVE:
                return "CLOSED"
            else:
                return "OPEN"
        except Exception as e:
            logger.error(f"Failed to read door sensor: {e}")
            return "UNKNOWN"

    def pulse(self) -> bool:
        """
        Send a pulse to the relay (ON, wait, OFF).
        
        This simulates pressing a button - the relay closes briefly
        then opens again.

        Returns:
            True if pulse was successful, False otherwise
        """
        if self._simulation_mode:
            logger.info(f"[SIMULATION] Pulsing GPIO{self.pin} for {self.pulse_duration_ms}ms")
            time.sleep(self.pulse_duration_ms / 1000.0)
            return True

        if not self._ensure_request():
            return False

        try:
            # Turn ON
            self._request.set_value(self.pin, self._get_on_value())
            logger.info(f"GPIO{self.pin} -> ON")

            # Wait
            time.sleep(self.pulse_duration_ms / 1000.0)

            # Turn OFF
            self._request.set_value(self.pin, self._get_off_value())
            logger.info(f"GPIO{self.pin} -> OFF")

            return True
        except Exception as e:
            logger.error(f"Failed to pulse GPIO: {e}")
            return False

    def cleanup(self):
        """Release GPIO resources."""
        if self._request is not None:
            try:
                self._request.release()
                logger.info("GPIO relay resources released")
            except Exception as e:
                logger.error(f"Error releasing GPIO: {e}")
            finally:
                self._request = None

        if self._sensor_request is not None:
            try:
                self._sensor_request.release()
                logger.info("GPIO sensor resources released")
            except Exception as e:
                logger.error(f"Error releasing sensor GPIO: {e}")
            finally:
                self._sensor_request = None

    def __del__(self):
        """Ensure cleanup on destruction."""
        self.cleanup()


# Singleton instance - will be initialized by main.py
_controller: Optional[GPIOController] = None


def get_controller() -> Optional[GPIOController]:
    """Get the global GPIO controller instance."""
    return _controller


def init_controller(
    chip_path: str,
    pin: int,
    active_high: bool,
    pulse_duration_ms: int,
    door_sensor_pin: int = 27
) -> GPIOController:
    """
    Initialize the global GPIO controller.

    Args:
        chip_path: Path to the GPIO chip device
        pin: GPIO pin number
        active_high: True if relay activates on HIGH
        pulse_duration_ms: Pulse duration in milliseconds
        door_sensor_pin: GPIO pin for door reed sensor

    Returns:
        The initialized GPIOController instance
    """
    global _controller
    if _controller is not None:
        _controller.cleanup()
    
    _controller = GPIOController(
        chip_path=chip_path,
        pin=pin,
        active_high=active_high,
        pulse_duration_ms=pulse_duration_ms,
        door_sensor_pin=door_sensor_pin
    )
    return _controller
