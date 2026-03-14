class DomainValidationError(Exception):
    """Raised when user-supplied data does not satisfy business rules."""


class FeatureNotImplementedError(Exception):
    """Raised when a selected feature exists in the contract but not in code yet."""


class ResourceNotFoundError(Exception):
    """Raised when the requested entity does not exist."""


class ExternalMLServiceError(Exception):
    """Raised when the external ML service is unavailable or returns invalid data."""
