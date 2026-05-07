class OtoeError(Exception):
    """Base error for developer-facing Otoe runtime failures."""


class UnknownPropError(OtoeError):
    """Raised when a widget receives a prop/event that its schema does not declare."""


class DuplicatePrimaryPropError(OtoeError):
    """Raised when a widget receives primary content and the matching kwarg."""


class EventHandlerError(OtoeError):
    """Raised when an event value is not callable."""


class ReactiveDisposedError(OtoeError):
    """Raised when code reads reactive state after its owner was disposed."""
