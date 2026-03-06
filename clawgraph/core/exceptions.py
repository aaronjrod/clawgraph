"""Custom exceptions for ClawGraph."""


class ClawGraphError(Exception):
    """Base exception for all ClawGraph errors."""


class SchemaVersionError(ClawGraphError):
    """Raised when a ClawOutput has an incompatible schema_version.

    - version > current: Reject (cannot process future schema).
    - version < current: No migration registered.
    """

    def __init__(self, received: int, current: int) -> None:
        self.received = received
        self.current = current
        direction = "future" if received > current else "outdated"
        super().__init__(
            f"Schema version mismatch: received v{received} "
            f"(current v{current}). Output is {direction}."
        )


class BagContractError(ClawGraphError):
    """Raised when a node output violates the Bag's I/O contract. (F-REQ-25)"""


class ManifestLockedError(ClawGraphError):
    """Raised when CRUD is attempted on a bag whose manifest is locked.

    The manifest is locked while a job is active to prevent mid-execution
    state drift.
    """

    def __init__(self, bag_name: str) -> None:
        self.bag_name = bag_name
        super().__init__(
            f"Bag '{bag_name}' manifest is locked (job in progress). "
            f"Cannot modify nodes while a job is active."
        )
