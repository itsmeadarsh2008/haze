"""
ID generation for Haze
"""

import uuid
from typing import Optional

from .exceptions import MissingDependencyError
from .utils import import_optional


def create_nanoid(size: int = 21, alphabet: Optional[str] = None) -> str:
    """Create a NanoID.

    Args:
        size: Length of the ID
        alphabet: Custom alphabet to use

    Returns:
        Generated NanoID
    """
    try:
        nanoid = import_optional("nanoid", "nanoid generation")
        if alphabet:
            return nanoid.generate(alphabet, size)
        return nanoid.generate(size=size)
    except MissingDependencyError:
        # Fall back to UUID if nanoid is not available
        return str(uuid.uuid4()).replace("-", "")[:size]


def create_uuid(
    version: int = 4, namespace: Optional[uuid.UUID] = None, name: Optional[str] = None
) -> str:
    """Create a UUID.

    Args:
        version: UUID version (4 or 5)
        namespace: Namespace for v5 UUID
        name: Name for v5 UUID

    Returns:
        Generated UUID
    """
    if version == 4:
        return str(uuid.uuid4())
    elif version == 5:
        if not namespace or not name:
            raise ValueError("Namespace and name required for UUID v5")
        return str(uuid.uuid5(namespace, name))
    else:
        raise ValueError(f"Unsupported UUID version: {version}")
