"""
Exception classes for Haze
"""


class HazeError(Exception):
    """Base exception for Haze."""

    pass


class ConfigError(HazeError):
    """Configuration error."""

    pass


class InvalidTokenError(HazeError):
    """Invalid token error."""

    pass


class ExpiredTokenError(InvalidTokenError):
    """Token expired error."""

    pass


class RateLimitError(HazeError):
    """Rate limit exceeded error."""

    pass


class StorageError(HazeError):
    """Storage error."""

    pass


class MissingDependencyError(HazeError):
    """Missing optional dependency error."""

    def __init__(self, module_name, purpose=None):
        message = f"Missing optional dependency '{module_name}'"
        if purpose:
            message += f" for {purpose}"
        message += f". Install with 'pip install {module_name}'"
        super().__init__(message)
