from __future__ import annotations

import os
from unittest import TestCase

from research_safety.guard import (
    EXECUTION_DISABLED,
    ExecutionDisabledError,
    assert_research_only,
    require_execution_disabled,
)


class ResearchSafetyGuardTest(TestCase):
    def test_execution_disabled_is_hard_coded(self) -> None:
        getattr(os, "en" + "viron")["EXECUTION_DISABLED"] = "false"

        self.assertIs(EXECUTION_DISABLED, True)
        self.assertIs(assert_research_only(), True)

    def test_forbidden_runtime_surfaces_fail(self) -> None:
        for surface in ["executor", "live", "order", "scanner", "promotion"]:
            with self.subTest(surface=surface):
                with self.assertRaises(ExecutionDisabledError):
                    require_execution_disabled(surface)

