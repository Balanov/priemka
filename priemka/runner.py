"""Прогон пакета проверок и сбор доказательств."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from .checks import CheckOutcome, run_gate
from .policy import Pack


@dataclass
class GateResult:
    """Результат гейта с доказательствами."""

    id: str
    kind: str
    description: str
    severity: str
    passed: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        return self.severity == "blocking"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "description": self.description,
            "severity": self.severity,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": self.evidence,
        }


@dataclass
class RunResult:
    """Итог прогона пакета."""

    pack: Pack
    results: list[GateResult]
    started_at: str
    finished_at: str

    @property
    def failed_blocking(self) -> list[GateResult]:
        return [result for result in self.results if result.blocking and not result.passed]

    @property
    def failed_advisory(self) -> list[GateResult]:
        return [result for result in self.results if not result.blocking and not result.passed]

    @property
    def accepted(self) -> bool:
        """Fail-closed: система принята, только если все блокирующие гейты пройдены."""
        return not self.failed_blocking

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.pack.name,
            "target": self.pack.target,
            "description": self.pack.description,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "accepted": self.accepted,
            "verdict": "ПРИНЯТО" if self.accepted else "НЕ ПРИНЯТО",
            "gatesTotal": len(self.results),
            "gatesPassed": sum(1 for result in self.results if result.passed),
            "failedBlocking": [result.id for result in self.failed_blocking],
            "failedAdvisory": [result.id for result in self.failed_advisory],
            "stopConditions": self.pack.stop_conditions,
            "gates": [result.to_dict() for result in self.results],
        }


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def run_pack(pack: Pack) -> RunResult:
    """Выполняет все гейты пакета по порядку."""
    started = now_iso()
    results: list[GateResult] = []
    for gate in pack.gates:
        outcome: CheckOutcome = run_gate(gate, pack.target)
        results.append(GateResult(
            id=gate.id,
            kind=gate.kind,
            description=gate.description,
            severity=gate.severity,
            passed=outcome.passed,
            detail=outcome.evidence.detail,
            evidence=outcome.evidence.to_dict(),
        ))
    return RunResult(pack=pack, results=results, started_at=started, finished_at=now_iso())
