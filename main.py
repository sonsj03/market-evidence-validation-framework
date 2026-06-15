from __future__ import annotations

from core.research_only_runtime_guard import research_only_mode_enabled
from core.startup_readiness import record_startup_event, reset_startup_readiness


def main() -> int:
    reset_startup_readiness()
    if research_only_mode_enabled():
        detail = "research_only=true: 실행형 런타임 기동을 차단합니다. WS/Brain/Executor/Telegram/Sentinel/Screener not started."
        record_startup_event("ResearchOnlyHardStop", "BLOCKED_RUNTIME_ENTRYPOINT", detail=detail)
        print(detail)
        return 0

    _STALE_LOCKS = [
        "runtime/ws.lock",
        "runtime/brain.lock",
        "runtime/executor.lock",
    ]

    from core.executor import executor_worker
    from core.brain import brain_worker
    from core.altcoin_screener import altcoin_screener_worker

    processes = [executor_worker, brain_worker, altcoin_screener_worker]
    raise RuntimeError(f"runtime execution is unavailable in this public build: {processes}")


if __name__ == "__main__":
    raise SystemExit(main())
