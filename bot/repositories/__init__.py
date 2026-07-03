"""Repository layer — encapsulates all database access.

Handlers and services never touch the ORM session directly; they go through
these repositories, which use parameterised queries exclusively (SQL injection
safe by construction).
"""

from bot.repositories.favorite_repo import FavoriteRepository
from bot.repositories.query_repo import QueryRepository
from bot.repositories.user_repo import UserRepository

__all__ = ["UserRepository", "QueryRepository", "FavoriteRepository"]
