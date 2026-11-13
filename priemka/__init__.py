"""Приёмка — проверяемый допуск ИИ-систем в эксплуатацию.

Пакет готовит пакет проверок (policy pack), выполняет его против работающей
системы и выпускает доказательный отчёт: вердикт fail-closed, хеши ответов,
время ответа и ссылка на каждый гейт.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .policy import Pack, Gate, load_pack
from .runner import RunResult, GateResult, run_pack
from .report import render_markdown, verdict_of

__all__ = [
    "Pack",
    "Gate",
    "load_pack",
    "RunResult",
    "GateResult",
    "run_pack",
    "render_markdown",
    "verdict_of",
    "__version__",
]
