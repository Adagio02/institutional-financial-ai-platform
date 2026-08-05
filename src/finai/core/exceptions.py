class FinAIError(Exception):
    """Base application exception."""


class ResourceNotFoundError(FinAIError):
    """Raised when a requested resource cannot be found."""


class ConflictError(FinAIError):
    """Raised when an operation conflicts with stored data."""


class ProviderError(FinAIError):
    """Base market-data provider exception."""


class UnsupportedProviderError(ProviderError):
    """Raised when a provider name is unsupported."""
