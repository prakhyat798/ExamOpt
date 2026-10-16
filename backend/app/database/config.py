"""
ExamOpt Database Configuration
Handles backend selection (sqlite vs supabase) and non-sensitive status introspection.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

from app.database.exceptions import ConfigurationError


class DatabaseBackend(str, Enum):
    SQLITE = "sqlite"
    SUPABASE = "supabase"


class DatabaseConfig:
    """Manages database backend settings and credential validation."""

    def __init__(
        self,
        backend: Optional[str] = None,
        sqlite_db_path: Optional[Path] = None,
        supabase_url: Optional[str] = None,
        supabase_publishable_key: Optional[str] = None,
        supabase_secret_key: Optional[str] = None,
    ):
        raw_backend = (backend or os.getenv("DATABASE_BACKEND", "sqlite")).strip().lower()
        if raw_backend not in (DatabaseBackend.SQLITE.value, DatabaseBackend.SUPABASE.value):
            raise ConfigurationError(
                f"Unsupported DATABASE_BACKEND: '{raw_backend}'. Supported options are: 'sqlite', 'supabase'."
            )
        self.backend = DatabaseBackend(raw_backend)

        base_dir = Path(__file__).resolve().parent.parent.parent
        self.sqlite_db_path = sqlite_db_path or Path(os.getenv("SQLITE_DB_PATH", str(base_dir / "examopt.db")))

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_publishable_key = supabase_publishable_key or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        self.supabase_secret_key = supabase_secret_key or os.getenv("SUPABASE_SECRET_KEY")

    def validate(self) -> None:
        """Validates configuration parameters for the selected backend."""
        if self.backend == DatabaseBackend.SUPABASE:
            if not self.supabase_url:
                raise ConfigurationError(
                    "Supabase configuration missing: 'SUPABASE_URL' is required when DATABASE_BACKEND=supabase."
                )
            if not (self.supabase_secret_key or self.supabase_publishable_key):
                raise ConfigurationError(
                    "Supabase configuration missing: At least one of 'SUPABASE_SECRET_KEY' or "
                    "'SUPABASE_PUBLISHABLE_KEY' is required when DATABASE_BACKEND=supabase."
                )

    def get_safe_status(self) -> Dict[str, Any]:
        """
        Returns an observable, non-sensitive backend status dictionary.
        NEVER prints or leaks actual API keys, secrets, or connection strings.
        """
        sqlite_exists = self.sqlite_db_path.exists()
        supabase_configured = bool(self.supabase_url and (self.supabase_secret_key or self.supabase_publishable_key))

        return {
            "configured_backend": self.backend.value,
            "is_cloud": self.backend == DatabaseBackend.SUPABASE,
            "sqlite": {
                "available": sqlite_exists,
                "path": str(self.sqlite_db_path)
            },
            "supabase": {
                "configured": supabase_configured,
                "url_set": bool(self.supabase_url),
                "key_set": bool(self.supabase_secret_key or self.supabase_publishable_key)
            }
        }
