"""
ExamOpt Database Exceptions
Typed exceptions for database connectivity, authentication, configuration, and constraints.
"""


class DatabaseError(Exception):
    """Base exception for all ExamOpt database errors."""
    pass


class ConfigurationError(DatabaseError):
    """Raised when database configuration is missing, malformed, or unsupported."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when connection to the database cannot be established."""
    pass


class DatabaseAuthenticationError(DatabaseError):
    """Raised when credentials or tokens are rejected by the database service."""
    pass


class EntityNotFoundError(DatabaseError):
    """Raised when a requested database entity or row does not exist."""
    pass


class DatabaseIntegrityError(DatabaseError):
    """Raised when a primary key, foreign key, or check constraint is violated."""
    pass
