"""Configuration management for GaragePi."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # API Security
        self.api_key: str = os.getenv("API_KEY", "")
        if not self.api_key or self.api_key == "change-me-to-a-secure-random-string":
            raise ValueError(
                "API_KEY must be set in .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

        # GPIO Configuration
        self.gpio_chip: str = os.getenv("GPIO_CHIP", "/dev/gpiochip4")
        self.gpio_pin: int = int(os.getenv("GPIO_PIN", "17"))
        self.relay_active_high: bool = os.getenv("RELAY_ACTIVE_HIGH", "true").lower() == "true"

        # Timing
        self.pulse_duration_ms: int = int(os.getenv("PULSE_DURATION_MS", "500"))

        # Server
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))

    @property
    def relay_on_value(self) -> int:
        """Return the GPIO value that turns the relay ON."""
        return 1 if self.relay_active_high else 0

    @property
    def relay_off_value(self) -> int:
        """Return the GPIO value that turns the relay OFF."""
        return 0 if self.relay_active_high else 1


# Global settings instance
settings = Settings()
