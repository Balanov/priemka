"""Приёмка — проверяемый допуск ИИ-систем в эксплуатацию.

Пакет проверок прогоняется против работающей системы и превращается в отчёт:
вердикт, индекс готовности, разбивка по измерениям и подсказка, что чинить.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .checks import CHECKS, Evidence, Outcome
from .policy import DIMENSIONS, Gate, Pack, PolicyError, load_pack, starter_pack
from .report import render_console, render_markdown, verdict_of, write_report
from .runner import GateOutcome, RunResult, compare, run_pack
from .targets import Answer, FixtureTarget, HttpTarget, Target, build_target

__all__ = [
    "CHECKS",
    "DIMENSIONS",
    "Answer",
    "Evidence",
    "FixtureTarget",
    "Gate",
    "GateOutcome",
    "HttpTarget",
    "Outcome",
    "Pack",
    "PolicyError",
    "RunResult",
    "Target",
    "build_target",
    "compare",
    "load_pack",
    "render_console",
    "render_markdown",
    "run_pack",
    "starter_pack",
    "verdict_of",
    "write_report",
    "__version__",
]
