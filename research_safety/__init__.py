"""Research-only safety helpers."""

from .guard import EXECUTION_DISABLED, ExecutionDisabledError, require_execution_disabled

__all__ = [
    "EXECUTION_DISABLED",
    "ExecutionDisabledError",
    "require_execution_disabled",
]

