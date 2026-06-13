from __future__ import annotations

import importlib
import io
import os
import runpy
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any


RUNTIME_MODULES = [
    "core.logger",
    "core.ws_client",
    "core.brain",
    "core.executor",
    "core.telegram_bot",
    "core.llm_guard",
    "core.altcoin_screener",
]


def test_research_only_startup_guard_exits_before_runtime_imports_processes_locks_and_secrets(
) -> None:
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
    removed_paths: list[str] = []
    process_instantiations: list[dict[str, Any]] = []
    runtime_imports: list[str] = []

    startup_readiness = importlib.import_module("core.startup_readiness")
    runtime_guard = importlib.import_module("core.research_only_runtime_guard")

    def fake_reset_startup_readiness(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(("reset_startup_readiness", args, kwargs))
        return {"status": "TEST_RESET_ONLY"}

    def fake_record_startup_event(*args: Any, **kwargs: Any) -> None:
        calls.append(("record_startup_event", args, kwargs))

    class ForbiddenProcess:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            process_instantiations.append({"args": args, "kwargs": kwargs})
            raise AssertionError("research_only startup must not instantiate runtime processes")

    real_import = importlib.import_module

    def guarded_import_module(name: str, package: str | None = None) -> ModuleType:
        resolved = importlib.util.resolve_name(name, package) if name.startswith(".") and package else name
        if resolved in RUNTIME_MODULES:
            runtime_imports.append(resolved)
            raise AssertionError(f"research_only startup imported runtime module {resolved}")
        return real_import(name, package)

    import multiprocessing

    original_reset = startup_readiness.reset_startup_readiness
    original_record = startup_readiness.record_startup_event
    original_guard = runtime_guard.research_only_mode_enabled
    original_process = multiprocessing.Process
    original_import_module = importlib.import_module
    original_remove = os.remove
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code: int | None = None
    try:
        startup_readiness.reset_startup_readiness = fake_reset_startup_readiness
        startup_readiness.record_startup_event = fake_record_startup_event
        runtime_guard.research_only_mode_enabled = lambda *args, **kwargs: True
        multiprocessing.Process = ForbiddenProcess  # type: ignore[assignment]
        importlib.import_module = guarded_import_module
        os.remove = lambda path: removed_paths.append(str(path))  # type: ignore[assignment]
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                runpy.run_path(str(Path("main.py")), run_name="__main__")
        except SystemExit as exc:
            exit_code = int(exc.code or 0)
    finally:
        startup_readiness.reset_startup_readiness = original_reset
        startup_readiness.record_startup_event = original_record
        runtime_guard.research_only_mode_enabled = original_guard
        multiprocessing.Process = original_process
        importlib.import_module = original_import_module
        os.remove = original_remove

    output = stdout.getvalue() + stderr.getvalue()

    assert exit_code == 0
    assert ("reset_startup_readiness",) == (calls[0][0],)
    assert any(
        name == "record_startup_event"
        and args[:2] == ("ResearchOnlyHardStop", "BLOCKED_RUNTIME_ENTRYPOINT")
        and "WS/Brain/Executor/Telegram/Sentinel/Screener not started" in str(kwargs.get("detail", ""))
        for name, args, kwargs in calls
    )
    assert "research_only=true" in output
    assert "실행형 런타임 기동을 차단" in output
    assert process_instantiations == []
    assert runtime_imports == []
    assert removed_paths == []
    assert "exchange credential field" not in output
    assert "private credential field" not in output.lower()
    assert "notification credential field" not in output


def test_research_only_guard_reads_research_only_true_even_when_dry_run_true() -> None:
    from core.research_only_runtime_guard import research_only_mode_enabled

    with tempfile.TemporaryDirectory() as tmp:
        settings = Path(tmp) / "settings.yaml"
        settings.write_text(
            "mode:\n"
            "  research_only: true\n"
            "  dry_run: true\n",
            encoding="utf-8",
        )

        assert research_only_mode_enabled(str(settings)) is True


def test_main_places_research_only_guard_before_runtime_imports_and_lock_cleanup() -> None:
    source = Path("main.py").read_text(encoding="utf-8")

    guard_index = source.index("if research_only_mode_enabled():")
    executor_import_index = source.index("from core.executor import executor_worker")
    brain_import_index = source.index("from core.brain import brain_worker")
    scanner_import_index = source.index("from core.altcoin_screener import altcoin_screener_worker")
    lock_cleanup_index = source.index("_STALE_LOCKS = [")
    process_list_index = source.index("processes = [")

    assert guard_index < executor_import_index
    assert guard_index < brain_import_index
    assert guard_index < scanner_import_index
    assert guard_index < lock_cleanup_index
    assert guard_index < process_list_index
