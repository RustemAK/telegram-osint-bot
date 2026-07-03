"""User model, roles and per-user settings."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """Authorization roles, ordered from most to least privileged."""

    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"


class User(Base, TimestampMixin):
    """A Telegram user registered with the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Telegram user id (can exceed 32-bit range → BigInteger).
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Per-user settings ────────────────────────────────────────────────────
    # Preferred results-per-page for paginated views.
    page_size: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # Whether the user opted in to caching their query results.
    use_cache: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Preferred export format ("json" | "pdf").
    export_format: Mapped[str] = mapped_column(
        String(8), default="json", nullable=False
    )

    # ── Usage counters ───────────────────────────────────────────────────────
    total_queries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships (lazy-loaded to keep memory usage low).
    queries: Mapped[list["QueryLog"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    favorites: Mapped[list["Favorite"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} tg={self.telegram_id} role={self.role.value}>"
