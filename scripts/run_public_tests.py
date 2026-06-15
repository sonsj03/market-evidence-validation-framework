"""Run public test functions without third-party test dependencies."""

from __future__ import annotations

import importlib.util
import inspect
import sys
import tempfile
import traceback
from pathlib import Path
from types import ModuleType
from typing import Any


TEST_DIR = Path("tests")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_test(fn: Any) -> None:
    signature = inspect.signature(fn)
    kwargs: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name in signature.parameters:
            if name == "tmp_path":
                kwargs[name] = Path(tmp)
            else:
                raise RuntimeError(f"unsupported fixture '{name}' for {fn.__module__}.{fn.__name__}")
        fn(**kwargs)


def main() -> int:
    failures: list[str] = []
    total = 0
    for path in sorted(TEST_DIR.glob("test_*.py")):
        try:
            module = load_module(path)
        except Exception:
            failures.append(f"{path}: import failed\n{traceback.format_exc()}")
            continue
        for name, fn in sorted(vars(module).items()):
            if not name.startswith("test_") or not callable(fn):
                continue
            total += 1
            try:
                call_test(fn)
            except Exception:
                failures.append(f"{path}:{name} failed\n{traceback.format_exc()}")
    if failures:
        print(f"public tests: FAIL ({len(failures)} failed / {total} collected)")
        for failure in failures:
            print(failure)
        return 1
    print(f"public tests: PASS ({total} collected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
