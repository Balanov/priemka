"""Исполнение пакета проверок: вердикт, индекс готовности, разбивка по измерениям."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from .checks import CHECKS, DETERMINISTIC, Evidence, Outcome, check_determinism
from .policy import DIMENSION_LABELS, DIMENSIONS, Gate, Pack
from .targets import Answer, Target


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class GateOutcome:
    """Результат одного гейта с доказательством."""

    gate: Gate
    passed: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)
    fix: str = ""
    baseline_passed: bool | None = None
    baseline_detail: str = ""

    @property
    def id(self) -> str:
        return self.gate.id

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.gate.id,
            "kind": self.gate.kind,
            "dimension": self.gate.dimension,
            "dimensionLabel": self.gate.dimension_label,
            "severity": self.gate.severity,
            "weight": self.gate.weight,
            "description": self.gate.description,
            "passed": self.passed,
            "detail": self.detail,
            "fix": self.fix,
            "evidence": self.evidence,
        }
        if self.baseline_passed is not None:
            data["baselinePassed"] = self.baseline_passed
            data["baselineDetail"] = self.baseline_detail
            data["delta"] = "regression" if (self.baseline_passed and not self.passed) else (
                "improved" if (not self.baseline_passed and self.passed) else "same")
        return data


@dataclass
class RunResult:
    """Итог прогона пакета."""

    pack: Pack
    target: str
    outcomes: list[GateOutcome]
    started_at: str
    finished_at: str
    baseline: "RunResult | None" = None

    @property
    def failed_blocking(self) -> list[GateOutcome]:
        return [item for item in self.outcomes if item.gate.blocking and not item.passed]

    @property
    def failed_advisory(self) -> list[GateOutcome]:
        return [item for item in self.outcomes if not item.gate.blocking and not item.passed]

    @property
    def regressions(self) -> list[GateOutcome]:
        return [item for item in self.outcomes if item.baseline_passed and not item.passed]

    @property
    def accepted(self) -> bool:
        """Fail-closed: любой проваленный блокирующий гейт — система не принята."""
        return not self.failed_blocking

    @property
    def score(self) -> float:
        """Индекс готовности 0–100: взвешенная доля пройденных гейтов."""
        total = sum(item.gate.weight for item in self.outcomes)
        if not total:
            return 0.0
        earned = sum(item.gate.weight for item in self.outcomes if item.passed)
        return round(earned / total * 100, 1)

    @property
    def grade(self) -> str:
        if not self.accepted:
            return "НЕ ПРИНЯТО"
        if self.score >= 90:
            return "ПРИНЯТО"
        if self.score >= 70:
            return "ПРИНЯТО С ОГОВОРКАМИ"
        return "НЕ ПРИНЯТО"

    def dimensions(self) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for dimension in DIMENSIONS:
            items = [item for item in self.outcomes if item.gate.dimension == dimension]
            if not items:
                continue
            total = sum(item.gate.weight for item in items)
            earned = sum(item.gate.weight for item in items if item.passed)
            grouped[dimension] = {
                "label": DIMENSION_LABELS.get(dimension, dimension),
                "score": round(earned / total * 100, 1) if total else 0.0,
                "passed": sum(1 for item in items if item.passed),
                "total": len(items),
            }
        return grouped

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.pack.name,
            "target": self.target,
            "description": self.pack.description,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "accepted": self.accepted,
            "verdict": self.grade,
            "score": self.score,
            "gatesTotal": len(self.outcomes),
            "gatesPassed": sum(1 for item in self.outcomes if item.passed),
            "failedBlocking": [item.id for item in self.failed_blocking],
            "failedAdvisory": [item.id for item in self.failed_advisory],
            "regressions": [item.id for item in self.regressions],
            "dimensions": self.dimensions(),
            "stopConditions": self.pack.stop_conditions,
            "gates": [item.to_dict() for item in self.outcomes],
            "baseline": self.baseline.to_dict() if self.baseline else None,
        }


def _run_gate(gate: Gate, target: Target, cache: dict[str, Answer]) -> tuple[Outcome, Answer]:
    question = str(gate.params.get("question", ""))
    if not question:
        return Outcome(False, Evidence(kind=gate.kind, detail="В гейте не задан question"), "Укажите вопрос, на который система должна ответить."), Answer(text="")

    answer = cache.get(question)
    if answer is None:
        answer = target.ask(question)
        cache[question] = answer

    if gate.kind in DETERMINISTIC:
        second = target.ask(question)
        outcome = check_determinism(gate.params, answer, second)
        return outcome, answer

    if answer.failed:
        return Outcome(False, Evidence(kind=gate.kind, detail=f"Система недоступна: {answer.error}", latency_ms=answer.latency_ms), "Проверьте доступность сервиса и формат ответа."), answer

    handler = CHECKS.get(gate.kind)
    if handler is None:
        return Outcome(False, Evidence(kind=gate.kind, detail=f"Неизвестный вид проверки: {gate.kind}"), "Список видов: priemka rules"), answer
    return handler(gate.params, answer), answer


def run_pack(pack: Pack, target: Target) -> RunResult:
    """Выполняет все гейты пакета и считает вердикт и индекс готовности."""
    started = now_iso()
    cache: dict[str, Answer] = {}
    outcomes: list[GateOutcome] = []
    for gate in pack.gates:
        outcome, answer = _run_gate(gate, target, cache)
        outcomes.append(GateOutcome(
            gate=gate,
            passed=outcome.passed,
            detail=outcome.evidence.detail,
            evidence=outcome.evidence.to_dict(),
            fix=outcome.fix or gate.fix,
        ))
    return RunResult(
        pack=pack,
        target=target.describe(),
        outcomes=outcomes,
        started_at=started,
        finished_at=now_iso(),
    )


def compare(baseline: RunResult, current: RunResult) -> RunResult:
    """Добавляет к текущему прогону разницу с базовой системой."""
    baseline_by_id = {item.id: item for item in baseline.outcomes}
    for item in current.outcomes:
        reference = baseline_by_id.get(item.id)
        if reference is not None:
            item.baseline_passed = reference.passed
            item.baseline_detail = reference.detail
    current.baseline = baseline
    return current
