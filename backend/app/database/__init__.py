"""
ExamOpt Database Package
Unified data access layer supporting both local SQLite and Supabase PostgreSQL.
"""

from app.database.config import DatabaseBackend, DatabaseConfig
from app.database.exceptions import (
    DatabaseError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    EntityNotFoundError,
    DatabaseIntegrityError
)
from app.database.base import DatabaseRepository
from app.database.sqlite_repository import SQLiteRepository
from app.database.supabase_repository import SupabaseRepository
from app.database.factory import get_repository, reset_repository

__all__ = [
    "DatabaseBackend",
    "DatabaseConfig",
    "DatabaseError",
    "ConfigurationError",
    "DatabaseConnectionError",
    "DatabaseAuthenticationError",
    "EntityNotFoundError",
    "DatabaseIntegrityError",
    "DatabaseRepository",
    "SQLiteRepository",
    "SupabaseRepository",
    "get_repository",
    "reset_repository"
]
