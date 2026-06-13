"""Research-only runtime entrypoint guard.

This helper reads only public settings and
never merges private secret configuration.  It is used by ``main.py`` to fail closed
before WS/Brain/Executor-style runtime processes can start.
"""

from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def research_only_mode_enabled(settings_path: str | None = None) -> bool:
    path = Path(
        settings_path
        or BASE_DIR / "config" / "settings.yaml"
    )
    try:
        import yaml

        with path.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception:
        return True
    mode = cfg.get("mode") if isinstance(cfg, dict) else {}
    return bool(mode.get("research_only", False)) if isinstance(mode, dict) else False
