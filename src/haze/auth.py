"""
Core authentication logic for Haze
"""

import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Union

from .exceptions import (
    ConfigError,
    ExpiredTokenError,
    InvalidTokenError,
    RateLimitError,
    StorageError,
)
from .id import create_nanoid, create_uuid
from .jwt import JWT
from .serializers import get_serializer
from .storage import MemoryStorage, StorageAdapter
from .utils import encode_url_safe, now, parse_url


class MagicLink:
    """Magic link authentication handler."""

    def __init__(
        self,
        config,
        storage_handler=None,
        verification_handlers=None,
        click_handlers=None,
    ):
        """Initialize magic link handler.

        Args:
            config: Configuration object
            storage_handler: Optional storage handler function
            verification_handlers: Optional verification handlers
            click_handlers: Optional click handlers
        """
        self.config = config

        # Set up storage
        if storage_handler:
            self.storage = StorageAdapter(storage_handler)
        else:
            self.storage = MemoryStorage()

        # Set up JWT
        self.jwt = JWT(config)

        # Set up serializer
        serializer_name = config.get("serialization_format", "msgpack")
        self.serializer = get_serializer(serializer_name)

        # Set up handlers
        self.verification_handlers = verification_handlers or []
        self.click_handlers = click_handlers or []

        # Set up rate limiting
        self.rate_limit_data = {}

    def set_storage_handler(self, handler: Callable) -> None:
        """Set storage handler.

        Args:
            handler: Storage handler function
        """
        self.storage = StorageAdapter(handler)

    def add_verification_handler(self, handler: Callable) -> None:
        """Add verification handler.

        Args:
            handler: Verification handler function
        """
        if handler not in self.verification_handlers:
            self.verification_handlers.append(handler)

    def add_click_handler(self, handler: Callable) -> None:
        """Add click handler.

        Args:
            handler: Click handler function
        """
        if handler not in self.click_handlers:
            self.click_handlers.append(handler)

    def _generate_id(self) -> str:
        """Generate a unique token ID.

        Returns:
            Unique token ID
        """
        id_generator = self.config.get("id_generator", "nanoid")

        if id_generator == "nanoid":
            size = self.config.get("nanoid_size", 21)
            alphabet = self.config.get("nanoid_alphabet")
            return create_nanoid(size, alphabet)
        elif id_generator == "uuid":
            version = self.config.get("uuid_version", 4)
            namespace = self.config.get("uuid_namespace")
            name = f"haze-{time.time()}"
            return create_uuid(version, namespace, name)
        else:
            raise ConfigError(f"Unsupported ID generator: {id_generator}")

    def _check_rate_limit(self, user_id: str) -> None:
        """Check if rate limit is exceeded.

        Args:
            user_id: User identifier

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        rate_limit = self.config.get("rate_limit", {})
        if not rate_limit.get("enabled", True):
            return

        max_attempts = rate_limit.get("max_attempts", 5)
        window_seconds = rate_limit.get("window_seconds", 300)

        # Get current limits
        current_time = now()
        key = f"rate_limit:{user_id}"
        limits = self.rate_limit_data.get(
            key, {"attempts": 0, "window_start": current_time}
        )

        # Reset if window expired
        if current_time - limits["window_start"] > window_seconds:
            limits = {"attempts": 0, "window_start": current_time}

        # Check limit
        if limits["attempts"] >= max_attempts:
            time_left = window_seconds - (current_time - limits["window_start"])
            raise RateLimitError(
                f"Rate limit exceeded. Try again in {time_left} seconds."
            )

        # Update counter
        limits["attempts"] += 1
        self.rate_limit_data[key] = limits

    def _trigger_verification(self, user_id: str, token_data: Dict[str, Any]) -> None:
        """Trigger verification handlers.

        Args:
            user_id: User identifier
            token_data: Token data
        """
        for handler in self.verification_handlers:
            try:
                handler(user_id, token_data)
            except Exception as e:
                # Log error but don't fail
                print(f"Error in verification handler: {str(e)}")

    def _trigger_click(self, user_id: str, user_data: Dict[str, Any]) -> None:
        """Trigger click handlers.

        Args:
            user_id: User identifier
            user_data: User data
        """
        for handler in self.click_handlers:
            try:
                handler(user_id, user_data)
            except Exception as e:
                # Log error but don't fail
                print(f"Error in click handler: {str(e)}")

    def generate(
        self, user_id: str, metadata: Dict[str, Any] = None, expiry: int = None
    ) -> str:
        """Generate a magic link for the specified user.

        Args:
            user_id: User identifier
            metadata: Additional metadata to include in the token
            expiry: Token expiration time in seconds (overrides config)

        Returns:
            Magic link URL
        """
        # Check rate limit
        self._check_rate_limit(user_id)

        # Generate token ID
        token_id = self._generate_id()

        # Calculate expiry
        current_time = now()
        expiry_seconds = expiry or self.config.get("link_expiry", 3600)
        expiry_time = current_time + expiry_seconds

        # Create token payload
        payload = {
            "sub": user_id,
            "jti": token_id,
            "iat": current_time,
            "exp": expiry_time,
            "one_time": not self.config.get("allow_reuse", False),
        }

        # Add metadata if provided
        if metadata:
            payload["metadata"] = metadata

        # Generate JWT
        token = self.jwt.encode(payload)

        # Store token if one-time use
        if payload["one_time"]:
            self.storage.set(
                token_id,
                {
                    "user_id": user_id,
                    "exp": expiry_time,
                    "metadata": metadata or {},
                    "consumed": False,
                    "created_at": current_time,
                },
            )

        # Build magic link URL
        base_url = self.config.get("base_url").rstrip("/")
        path = self.config.get("magic_link_path", "/auth/verify").lstrip("/")

        # Ensure we don't have double slashes
        url = (
            f"{base_url}/{path}?token_id={token_id}&signature={encode_url_safe(token)}"
        )

        # Trigger click handlers for tracking
        self._trigger_click(user_id, {"user_id": user_id, "metadata": metadata or {}})

        return url

    def verify(self, token_id: str, signature: str) -> Dict[str, Any]:
        """Verify a magic link token.

        Args:
            token_id: Token identifier
            signature: Token signature

        Returns:
            User data if verification succeeds

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredTokenError: If token is expired
        """
        try:
            # Decode and verify JWT
            payload = self.jwt.decode(signature)

            # Verify token ID matches
            if payload.get("jti") != token_id:
                raise InvalidTokenError("Token ID mismatch")

            # Check if one-time use
            if payload.get("one_time", True):
                token_data = self.storage.get(token_id)

                if not token_data:
                    raise InvalidTokenError("Token not found")

                if token_data.get("consumed", False):
                    raise InvalidTokenError("Token has already been used")

                # Mark token as consumed
                self.storage.update(token_id, {"consumed": True})

            # Prepare result
            user_id = payload.get("sub")
            metadata = payload.get("metadata", {})

            result = {
                "user_id": user_id,
                "token_id": token_id,
                "metadata": metadata,
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
            }

            # Trigger verification handlers
            self._trigger_verification(user_id, payload)

            return result

        except ExpiredTokenError:
            # Re-raise expired token errors
            raise
        except Exception as e:
            # Wrap other errors
            raise InvalidTokenError(f"Token verification failed: {str(e)}")

    def validate(self, url: str) -> Dict[str, Any]:
        """Validate a complete magic link URL.

        Args:
            url: Complete magic link URL

        Returns:
            User data if validation succeeds
        """
        # Parse URL
        params = parse_url(url)

        if "token_id" not in params or "signature" not in params:
            raise InvalidTokenError("Invalid magic link URL format")

        # Extract token ID and signature
        token_id = params["token_id"]
        signature = params["signature"]

        # Verify token
        return self.verify(token_id, signature)

    def consume(self, token_id: str) -> bool:
        """Mark a token as consumed/used.

        Args:
            token_id: Token identifier

        Returns:
            True if token was successfully consumed

        Raises:
            InvalidTokenError: If token is not found
        """
        token_data = self.storage.get(token_id)

        if not token_data:
            raise InvalidTokenError("Token not found")

        if token_data.get("consumed", False):
            return False

        self.storage.update(token_id, {"consumed": True})
        return True

    def serialize(self, data: Dict[str, Any]) -> bytes:
        """Serialize data using configured serializer.

        Args:
            data: Data to serialize

        Returns:
            Serialized data
        """
        return self.serializer.serialize(data)

    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize data using configured serializer.

        Args:
            data: Data to deserialize

        Returns:
            Deserialized data
        """
        return self.serializer.deserialize(data)
