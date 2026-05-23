class OtoeError(Exception):
    """Base error for developer-facing Otoe runtime failures."""


class UnknownPropError(OtoeError):
    """Raised when a widget receives a prop that its schema does not declare."""


class UnknownEventError(UnknownPropError):
    """Raised when a widget receives an event that its schema does not declare."""


class DuplicatePrimaryPropError(OtoeError):
    """Raised when a widget receives primary content and the matching kwarg."""


class EventHandlerError(OtoeError):
    """Raised when an event handler is invalid."""


class EventHandlerArityError(EventHandlerError):
    """Raised when an event handler cannot accept the event arguments."""


class ReactiveDisposedError(OtoeError):
    """Raised when code reads reactive state after its owner was disposed."""


class ReactiveMutationError(OtoeError):
    """Raised when reactive state is mutated from an unsafe runtime phase."""
