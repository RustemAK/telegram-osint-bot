"""Query history log model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class QueryLog(Base, TimestampMixin):
    """A single OSINT query issued by a user, stored for history & stats."""

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    query: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Whether the result came from the in-memory cache.
    cached: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Whether the query completed without error.
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Comma-separated list of sources that returned data.
    sources: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Error message when success is False (for the admin error view).
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Execution time in milliseconds.
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="queries")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<QueryLog id={self.id} q={self.query!r} type={self.query_type}>"
