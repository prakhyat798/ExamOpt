"""
ExamOpt Database Repository Factory
Provides dynamic instantiation of the active repository based on DATABASE_BACKEND setting.
"""

from typing import Optional

from app.database.config import DatabaseConfig, DatabaseBackend
from app.database.base import DatabaseRepository
from app.database.sqlite_repository import SQLiteRepository
from app.database.supabase_repository import SupabaseRepository

_ACTIVE_REPOSITORY: Optional[DatabaseRepository] = None
_ACTIVE_CONFIG: Optional[DatabaseConfig] = None


def get_repository(config: Optional[DatabaseConfig] = None, force_refresh: bool = False) -> DatabaseRepository:
    """
    Returns the repository instance matching the active configuration.
    Raises ConfigurationError if DATABASE_BACKEND is unsupported or required cloud settings are missing.
    """
    global _ACTIVE_REPOSITORY, _ACTIVE_CONFIG

    if _ACTIVE_REPOSITORY is not None and not force_refresh and config is None:
        return _ACTIVE_REPOSITORY

    active_cfg = config or DatabaseConfig()
    active_cfg.validate()

    if active_cfg.backend == DatabaseBackend.SQLITE:
        repo = SQLiteRepository(active_cfg.sqlite_db_path)
    elif active_cfg.backend == DatabaseBackend.SUPABASE:
        repo = SupabaseRepository(active_cfg)
    else:
        # Should already be caught by DatabaseConfig, but defensive guard
        raise ValueError(f"Unknown database backend: {active_cfg.backend}")

    _ACTIVE_REPOSITORY = repo
    _ACTIVE_CONFIG = active_cfg
    return repo


def reset_repository() -> None:
    """Resets the cached singleton repository (used during testing and reloads)."""
    global _ACTIVE_REPOSITORY, _ACTIVE_CONFIG
    _ACTIVE_REPOSITORY = None
    _ACTIVE_CONFIG = None
