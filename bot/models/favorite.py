"""Favorites model — users can bookmark queries for quick re-running."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class Favorite(Base, TimestampMixin):
    """A saved (bookmarked) query belonging to a user."""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "query", name="uq_favorite_user_query"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    query: Mapped[str] = mapped_column(String(256), nullable=False)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)

    user: Mapped["User"] = relationship(back_populates="favorites")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Favorite id={self.id} q={self.query!r}>"
