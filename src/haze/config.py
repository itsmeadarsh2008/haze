"""
Configuration management for Haze
"""

import secrets
from typing import Any, Dict

from .exceptions import ConfigError


class Config:
    """Configuration management for Haze."""

    def __init__(self):
        """Initialize with default configuration."""
        self._defaults = {
            # Base settings
            "base_url": "http://localhost:8000",
            "magic_link_path": "/auth/verify",
            "link_expiry": 3600,  # 1 hour
            "allow_reuse": False,  # one-time use by default
            # Security settings
            "secret_key": None,  # Must be set by user
            "private_key": None,  # For asymmetric keys
            "public_key": None,  # For asymmetric keys
            # Provider settings
            "token_provider": "jwt",  # Only JWT supported
            "id_generator": "nanoid",  # nanoid or uuid
            "serialization_format": "msgpack",  # msgpack or json
            # Token options
            "jwt_algorithm": "HS256",  # HS256, RS256, ES256
            "token_issuer": "haze",
            "token_audience": None,
            # ID generation options
            "nanoid_size": 21,
            "nanoid_alphabet": "_-0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "uuid_version": 4,
            "uuid_namespace": None,
            # Security features
            "rate_limit": {
                "enabled": True,
                "max_attempts": 5,
                "window_seconds": 300,  # 5 minutes
            },
            "fingerprint": {
                "enabled": False,
                "factors": ["ip", "user_agent"],
            },
        }

        self._config = self._defaults.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        parts = key.split(".")
        current = self._config

        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        parts = key.split(".")
        current = self._config

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def update(self, config: Dict[str, Any]) -> None:
        """Update multiple configuration values.

        Args:
            config: Dictionary of configuration values
        """
        for key, value in config.items():
            if value is not None:  # Only update if value is not None
                if "." in key:
                    self.set(key, value)
                else:
                    self._config[key] = value

        # Validate configuration
        self.validate()

    def validate(self) -> None:
        """Validate configuration values."""
        if self._config["token_provider"] != "jwt":
            raise ConfigError(
                f"Unsupported token provider: {self._config['token_provider']}"
            )

        # Validate JWT configuration
        if self._config["jwt_algorithm"].startswith("HS"):
            if not self._config["secret_key"]:
                # Auto-generate secret key if not provided
                self._config["secret_key"] = secrets.token_hex(32)
        elif self._config["jwt_algorithm"].startswith(("RS", "ES")):
            if not self._config["private_key"] or not self._config["public_key"]:
                raise ConfigError(
                    f"Private and public keys required for {self._config['jwt_algorithm']}"
                )

        # Validate ID generator
        if self._config["id_generator"] not in ["nanoid", "uuid"]:
            raise ConfigError(
                f"Unsupported ID generator: {self._config['id_generator']}"
            )

        # Validate serialization format
        if self._config["serialization_format"] not in ["msgpack", "json"]:
            raise ConfigError(
                f"Unsupported serialization format: {self._config['serialization_format']}"
            )
