"""Configuration package.

Provides the strongly-typed :class:`Settings` object loaded from the
environment (``.env``) via pydantic-settings.
"""

from bot.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
