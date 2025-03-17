"""
JWT implementation for Haze
"""

import time
from typing import Any, Dict, Optional, Union

from .exceptions import ExpiredTokenError, InvalidTokenError, MissingDependencyError
from .utils import import_optional, now


class JWT:
    """JWT implementation."""

    def __init__(self, config):
        """Initialize JWT with configuration.

        Args:
            config: Configuration object
        """
        self.config = config
        self.jwt = import_optional("jwt", "JWT support")

    def encode(self, payload: Dict[str, Any]) -> str:
        """Encode payload as JWT.

        Args:
            payload: Data to encode

        Returns:
            Encoded JWT
        """
        algorithm = self.config.get("jwt_algorithm", "HS256")

        # Add standard claims if not present
        if "iat" not in payload:
            payload["iat"] = now()

        if "exp" not in payload:
            payload["exp"] = now() + self.config.get("link_expiry", 3600)

        if "iss" not in payload and self.config.get("token_issuer"):
            payload["iss"] = self.config.get("token_issuer")

        if "aud" not in payload and self.config.get("token_audience"):
            payload["aud"] = self.config.get("token_audience")

        # Sign with appropriate key
        if algorithm.startswith("HS"):
            key = self.config.get("secret_key")
            if not key:
                raise InvalidTokenError("Secret key required for HS* algorithms")
        elif algorithm.startswith(("RS", "ES")):
            key = self.config.get("private_key")
            if not key:
                raise InvalidTokenError(f"Private key required for {algorithm}")
        else:
            raise InvalidTokenError(f"Unsupported algorithm: {algorithm}")

        try:
            return self.jwt.encode(payload, key, algorithm=algorithm)
        except Exception as e:
            raise InvalidTokenError(f"JWT encoding failed: {str(e)}")

    def decode(
        self,
        token: str,
        verify: bool = True,
        verify_exp: bool = True,
        audience: Optional[str] = None,
        issuer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Decode and verify JWT.

        Args:
            token: JWT to decode
            verify: Whether to verify the signature
            verify_exp: Whether to verify expiration
            audience: Expected audience
            issuer: Expected issuer

        Returns:
            Decoded payload

        Raises:
            InvalidTokenError: If token is invalid or verification fails
            ExpiredTokenError: If token is expired
        """
        algorithm = self.config.get("jwt_algorithm", "HS256")

        # Get appropriate key for verification
        if algorithm.startswith("HS"):
            key = self.config.get("secret_key")
            if not key:
                raise InvalidTokenError("Secret key required for HS* algorithms")
        elif algorithm.startswith(("RS", "ES")):
            key = self.config.get("public_key")
            if not key:
                raise InvalidTokenError(f"Public key required for {algorithm}")
        else:
            raise InvalidTokenError(f"Unsupported algorithm: {algorithm}")

        # Set verification options
        options = {
            "verify_signature": verify,
            "verify_exp": verify_exp,
            "verify_iat": True,
        }

        # Set audience and issuer if provided
        if audience is None:
            audience = self.config.get("token_audience")

        if issuer is None:
            issuer = self.config.get("token_issuer")

        try:
            return self.jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                options=options,
                audience=audience,
                issuer=issuer,
            )
        except self.jwt.ExpiredSignatureError:
            raise ExpiredTokenError("Token has expired")
        except Exception as e:
            raise InvalidTokenError(f"JWT decoding failed: {str(e)}")
