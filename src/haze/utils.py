"""
Utility functions for Haze
"""

import importlib
import time
from typing import Any, Dict, Optional

from .exceptions import MissingDependencyError


def import_optional(name: str, purpose: Optional[str] = None) -> Any:
    """Import an optional dependency.

    Args:
        name: Module name
        purpose: Purpose of the module

    Returns:
        Imported module

    Raises:
        MissingDependencyError if module is not found
    """
    try:
        return importlib.import_module(name)
    except ImportError:
        raise MissingDependencyError(name, purpose)


def now() -> int:
    """Get current Unix timestamp.

    Returns:
        Current time as Unix timestamp
    """
    return int(time.time())


def encode_url_safe(data: str) -> str:
    """Encode string as URL-safe.

    Args:
        data: String to encode

    Returns:
        URL-safe encoded string
    """
    import urllib.parse

    return urllib.parse.quote(data, safe="")


def parse_url(url: str) -> Dict[str, str]:
    """Parse URL and extract query parameters.

    Args:
        url: URL to parse

    Returns:
        Dictionary of query parameters
    """
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    result = {}

    for key, values in query_params.items():
        if values:
            result[key] = values[0]

    return result
