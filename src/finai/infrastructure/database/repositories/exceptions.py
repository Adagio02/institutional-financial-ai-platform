class RepositoryError(Exception):
    """Base repository exception."""


class InstrumentAlreadyExistsError(RepositoryError):
    """Raised when an instrument symbol already exists."""


class InstrumentNotFoundError(RepositoryError):
    """Raised when an instrument cannot be found."""
