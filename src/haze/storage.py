"""
Storage interface for Haze
"""

import time
from typing import Dict, Any, Optional, Callable

from .exceptions import StorageError


class MemoryStorage:
    """In-memory storage implementation."""

    def __init__(self):
        """Initialize memory storage."""
        self.tokens = {}

    def get(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get token data.

        Args:
            token_id: Token identifier

        Returns:
            Token data or None if not found
        """
        return self.tokens.get(token_id)

    def set(self, token_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set token data.

        Args:
            token_id: Token identifier
            data: Token data

        Returns:
            Updated token data
        """
        self.tokens[token_id] = data
        return data

    def update(
        self, token_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update token data.

        Args:
            token_id: Token identifier
            update_data: Data to update

        Returns:
            Updated token data or None if not found
        """
        if token_id not in self.tokens:
            return None

        self.tokens[token_id].update(update_data)
        return self.tokens[token_id]

    def delete(self, token_id: str) -> bool:
        """Delete token data.

        Args:
            token_id: Token identifier

        Returns:
            True if token was deleted, False otherwise
        """
        if token_id in self.tokens:
            del self.tokens[token_id]
            return True
        return False

    def cleanup(self, max_age: int = None) -> int:
        """Clean up expired tokens.

        Args:
            max_age: Maximum age in seconds

        Returns:
            Number of tokens deleted
        """
        if max_age is None:
            return 0

        now = int(time.time())
        expired_tokens = [
            token_id
            for token_id, data in self.tokens.items()
            if data.get("exp", 0) < now
        ]

        for token_id in expired_tokens:
            self.delete(token_id)

        return len(expired_tokens)


class StorageAdapter:
    """Adapter for custom storage handlers."""

    def __init__(self, handler: Callable):
        """Initialize with custom handler.

        Args:
            handler: Custom storage handler function
        """
        self.handler = handler

    def get(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get token data using custom handler.

        Args:
            token_id: Token identifier

        Returns:
            Token data or None if not found
        """
        try:
            return self.handler(token_id)
        except Exception as e:
            raise StorageError(f"Storage get failed: {str(e)}")

    def set(self, token_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set token data using custom handler.

        Args:
            token_id: Token identifier
            data: Token data

        Returns:
            Updated token data
        """
        try:
            return self.handler(token_id, data)
        except Exception as e:
            raise StorageError(f"Storage set failed: {str(e)}")

    def update(
        self, token_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update token data using custom handler.

        Args:
            token_id: Token identifier
            update_data: Data to update

        Returns:
            Updated token data or None if not found
        """
        try:
            current_data = self.handler(token_id)
            if current_data is None:
                return None

            current_data.update(update_data)
            return self.handler(token_id, current_data)
        except Exception as e:
            raise StorageError(f"Storage update failed: {str(e)}")

    def delete(self, token_id: str) -> bool:
        """Delete token data using custom handler.

        Args:
            token_id: Token identifier

        Returns:
            True if token was deleted
        """
        try:
            self.handler(token_id, None)
            return True
        except Exception as e:
            raise StorageError(f"Storage delete failed: {str(e)}")
