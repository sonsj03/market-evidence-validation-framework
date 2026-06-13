"""Hard-coded research-only runtime guard.

This module deliberately does not read environment variables. Public copies of
this project must not expose a switch that enables execution behavior.
"""

from __future__ import annotations


EXECUTION_DISABLED = True


class ExecutionDisabledError(RuntimeError):
    """Raised when forbidden trading/runtime behavior is requested."""


FORBIDDEN_RUNTIME_SURFACES = frozenset(
    {
        "executor",
        "execution",
        "order",
        "order_execution",
        "live",
        "shadow",
        "scanner",
        "promotion",
        "private_exchange_api",
        "signed_exchange_api",
        "wallet",
        "account",
        "balance",
        "position",
        "telegram_trade_alert",
    }
)


def require_execution_disabled(surface: str) -> None:
    """Fail whenever a forbidden runtime surface is touched."""

    normalized = str(surface or "").strip().lower()
    if not EXECUTION_DISABLED:
        raise ExecutionDisabledError("execution guard was unexpectedly disabled")
    if normalized in FORBIDDEN_RUNTIME_SURFACES:
        raise ExecutionDisabledError(
            f"{normalized} is disabled: research-only validation framework"
        )


def assert_research_only() -> bool:
    """Return True only while execution remains hard-disabled."""

    if not EXECUTION_DISABLED:
        raise ExecutionDisabledError("execution must remain disabled")
    return True

