"""
Haze: Lightning-Fast Magic Link Authentication
"""

import functools
import secrets
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Union

from .auth import MagicLink
from .config import Config
from .exceptions import (
    ConfigError,
    HazeError,
    InvalidTokenError,
    RateLimitError,
    StorageError,
)

__version__ = "0.1.0"

# Initialize global state
_config = Config()
_instance = None
_storage_handler = None
_verification_handlers = []
_click_handlers = []


def use(
    base_url: str = None,
    magic_link_path: str = "/auth/verify",
    link_expiry: int = 3600,
    allow_reuse: bool = False,
    secret_key: str = None,
    private_key: Any = None,
    public_key: Any = None,
    token_provider: str = "jwt",
    id_generator: str = "nanoid",
    serialization_format: str = "msgpack",
    jwt_algorithm: str = "HS256",
    token_issuer: str = "haze",
    token_audience: str = None,
    nanoid_size: int = 21,
    nanoid_alphabet: str = None,
    uuid_version: int = 4,
    **kwargs,
) -> None:
    """Configure Haze with the specified options

    Args:
        base_url: Base URL for magic links
        magic_link_path: Path for verification endpoint
        link_expiry: Token expiration time in seconds
        allow_reuse: Whether tokens can be reused
        secret_key: Secret key for symmetric algorithms
        private_key: Private key for asymmetric algorithms
        public_key: Public key for asymmetric algorithms
        token_provider: Token provider to use (only "jwt" supported)
        id_generator: ID generator to use ("nanoid" or "uuid")
        serialization_format: Serialization format ("msgpack" or "json")
        jwt_algorithm: JWT algorithm to use (HS256, RS256, ES256)
        token_issuer: Token issuer name
        token_audience: Token audience
        nanoid_size: Size of generated NanoIDs
        nanoid_alphabet: Custom alphabet for NanoID
        uuid_version: UUID version (4 or 5)
        **kwargs: Additional configuration options
    """
    global _config, _instance, _storage_handler

    options = {
        "base_url": base_url or "http://localhost:8000",
        "magic_link_path": magic_link_path,
        "link_expiry": link_expiry,
        "allow_reuse": allow_reuse,
        "secret_key": secret_key or kwargs.get("secret_key"),
        "private_key": private_key,
        "public_key": public_key,
        "token_provider": token_provider,
        "id_generator": id_generator,
        "serialization_format": serialization_format,
        "jwt_algorithm": jwt_algorithm,
        "token_issuer": token_issuer,
        "token_audience": token_audience,
        "nanoid_size": nanoid_size,
        "nanoid_alphabet": nanoid_alphabet,
        "uuid_version": uuid_version,
    }

    # Add any additional kwargs
    options.update(kwargs)

    # Update config
    _config.update(options)

    # Create instance
    _instance = MagicLink(
        _config, _storage_handler, _verification_handlers, _click_handlers
    )
    return _instance


def storage(func: Callable) -> Callable:
    """Register a storage handler.

    Example:
    @haze.storage
    def store_token(token_id, data=None):
        if data is None:
            return token_store.get(token_id)
        token_store[token_id] = data
        return data
    """
    global _storage_handler, _instance
    _storage_handler = func

    if _instance:
        _instance.set_storage_handler(func)

    return func


def verification(func: Callable) -> Callable:
    """Register a verification handler.

    Example:
    @haze.verification
    def on_verification(user_id, token_data):
        print(f"User {user_id} verified with token")
    """
    global _verification_handlers, _instance
    _verification_handlers.append(func)

    if _instance:
        _instance.add_verification_handler(func)

    return func


def onclick(func: Callable) -> Callable:
    """Register a click handler.

    Example:
    @haze.onclick
    def on_link_clicked(user_id, user_data):
        print(f"User {user_id} clicked magic link")
    """
    global _click_handlers, _instance
    _click_handlers.append(func)

    if _instance:
        _instance.add_click_handler(func)

    return func


def _ensure_instance():
    """Ensure that the instance is initialized."""
    global _instance
    if _instance is None:
        use()
    return _instance


def generate(user_id: str, metadata: Dict[str, Any] = None, expiry: int = None) -> str:
    """Generate a magic link for the specified user.

    Args:
        user_id: User identifier
        metadata: Additional metadata to include in the token
        expiry: Token expiration time in seconds (overrides default)

    Returns:
        Magic link URL
    """
    instance = _ensure_instance()
    return instance.generate(user_id, metadata, expiry)


def verify(token_id: str, signature: str) -> Dict[str, Any]:
    """Verify a magic link token.

    Args:
        token_id: Token identifier
        signature: Token signature

    Returns:
        User data if verification succeeds
    """
    instance = _ensure_instance()
    return instance.verify(token_id, signature)


def validate(url: str) -> Dict[str, Any]:
    """Validate a complete magic link URL.

    Args:
        url: Complete magic link URL

    Returns:
        User data if validation succeeds
    """
    instance = _ensure_instance()
    return instance.validate(url)


def consume(token_id: str) -> bool:
    """Mark a token as consumed/used.

    Args:
        token_id: Token identifier

    Returns:
        True if token was successfully consumed
    """
    instance = _ensure_instance()
    return instance.consume(token_id)


def serialize(data: Dict[str, Any]) -> bytes:
    """Serialize data to bytes.

    Args:
        data: Data to serialize

    Returns:
        Serialized data
    """
    instance = _ensure_instance()
    return instance.serialize(data)


def deserialize(data: bytes) -> Dict[str, Any]:
    """Deserialize bytes to data.

    Args:
        data: Data to deserialize

    Returns:
        Deserialized data
    """
    instance = _ensure_instance()
    return instance.deserialize(data)
