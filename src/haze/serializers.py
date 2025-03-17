"""
Serialization utilities for Haze
"""

from typing import Any, Dict

from .exceptions import MissingDependencyError
from .utils import import_optional


class Serializer:
    """Base serializer interface."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data to bytes."""
        raise NotImplementedError

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize bytes to data."""
        raise NotImplementedError


class MsgpackSerializer(Serializer):
    """MsgPack serializer."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data to MsgPack format."""
        msgpack = import_optional("msgpack", "msgpack serialization")
        return msgpack.packb(data, use_bin_type=True)

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize MsgPack data."""
        msgpack = import_optional("msgpack", "msgpack serialization")
        return msgpack.unpackb(data, raw=False)


class JsonSerializer(Serializer):
    """JSON serializer."""

    @staticmethod
    def serialize(data: Any) -> bytes:
        """Serialize data to JSON format."""
        try:
            orjson = import_optional("orjson", "fast json serialization")
            return orjson.dumps(data)
        except MissingDependencyError:
            import json

            return json.dumps(data).encode("utf-8")

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize JSON data."""
        try:
            orjson = import_optional("orjson", "fast json serialization")
            return orjson.loads(data)
        except MissingDependencyError:
            import json

            return json.loads(data.decode("utf-8"))


def get_serializer(format_name: str) -> Serializer:
    """Get serializer by name.

    Args:
        format_name: Serializer name ('msgpack' or 'json')

    Returns:
        Serializer instance

    Raises:
        ValueError: If format is unsupported
    """
    if format_name == "msgpack":
        return MsgpackSerializer
    elif format_name == "json":
        return JsonSerializer
    else:
        raise ValueError(f"Unsupported serialization format: {format_name}")
