class DomainValidationError(Exception):
    """Raised when user-supplied data does not satisfy business rules."""


class FeatureNotImplementedError(Exception):
    """Raised when a selected feature exists in the contract but not in code yet."""


class ResourceNotFoundError(Exception):
    """Raised when the requested entity does not exist."""


class ExternalMLServiceError(Exception):
    """Raised when the external ML service is unavailable or returns invalid data."""


class ExternalMLRequestError(ExternalMLServiceError):
    """Raised when the external ML service request fails before a valid payload is returned."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ExternalMLResponseError(ExternalMLServiceError):
    """Raised when the external ML service returns an invalid or unusable payload."""
