"""Startup event helpers for the research-only public entrypoint."""

from __future__ import annotations

from typing import Any


def reset_startup_readiness(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"status": "RESET", "args": args, "kwargs": kwargs}


def record_startup_event(name: str, status: str, **kwargs: Any) -> None:
    print(f"{name}: {status} {kwargs.get('detail', '')}")
