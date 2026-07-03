"""Application settings.

All configuration is loaded from environment variables (typically via a
``.env`` file) using :mod:`pydantic_settings`. Secrets such as API keys are
*never* hard-coded — they live only in the environment.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application configuration.

    Attributes are populated from the environment. See ``.env.example`` for the
    full list of supported variables and their defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Telegram ─────────────────────────────────────────────────────────────
    bot_token: str = Field(..., description="Telegram bot token from @BotFather")
    admin_ids: list[int] = Field(default_factory=list, description="Admin user IDs")

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./osint_bot.db",
        description="Async SQLAlchemy database URL",
    )

    # ── Rate limiting / concurrency ─────────────────────────────────────────
    throttle_rate: float = Field(default=0.7, description="Min seconds between messages")
    daily_query_limit: int = Field(default=100, description="Max OSINT queries/user/day")
    max_concurrent_tasks: int = Field(default=8, description="Max parallel OSINT tasks")

    # ── Cache ────────────────────────────────────────────────────────────────
    cache_ttl: int = Field(default=600, description="In-memory cache TTL in seconds")
    cache_max_size: int = Field(default=512, description="Max cached entries")

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Logging level")
    log_to_file: bool = Field(default=True, description="Also write JSON logs to disk")

    # ── OSINT API keys (all optional) ────────────────────────────────────────
    virustotal_api_key: str | None = None
    shodan_api_key: str | None = None
    censys_api_id: str | None = None
    censys_api_secret: str | None = None
    securitytrails_api_key: str | None = None
    abuseipdb_api_key: str | None = None
    greynoise_api_key: str | None = None
    ipinfo_token: str | None = None
    github_token: str | None = None
    gitlab_token: str | None = None
    newsapi_key: str | None = None
    hibp_api_key: str | None = None

    # ── HTTP client ──────────────────────────────────────────────────────────
    http_timeout: float = Field(default=15.0, description="HTTP request timeout")
    http_user_agent: str = Field(
        default="OSINT-Bot/1.0 (+https://example.com)",
        description="User-Agent header for outbound requests",
    )

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> list[int]:
        """Accept a comma-separated string or a list of ids for ``ADMIN_IDS``."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple)):
            return [int(v) for v in value]
        return [int(value)]  # type: ignore[arg-type]

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        """Normalise the log level to upper case."""
        return value.upper()

    @property
    def is_sqlite(self) -> bool:
        """Return ``True`` when the configured database is SQLite."""
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Using an LRU cache guarantees the ``.env`` file is parsed exactly once,
    which keeps startup fast and memory usage minimal.
    """
    return Settings()  # type: ignore[call-arg]
