"""Реализации гейтов приёмки.

Все проверки детерминированные и наблюдаемые: каждый результат несёт
доказательство (хеш ответа, тело ответа, задержку), а не только «пройдено».
Система под вопросом вызывается локально по HTTP; наружу данные не уходят.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

DEFAULT_TIMEOUT = 30.0


@dataclass
class Evidence:
    """Доказательная часть результата гейта."""

    kind: str
    detail: str = ""
    answer_hash: str = ""
    answer_preview: str = ""
    latency_ms: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "kind": self.kind,
            "detail": self.detail,
            "answerSha256": self.answer_hash,
            "answerPreview": self.answer_preview,
            "latencyMs": self.latency_ms,
        }
        if self.extra:
            data["extra"] = self.extra
        return data


@dataclass
class CheckOutcome:
    """Результат одной попытки гейта."""

    passed: bool
    evidence: Evidence


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ask(target: str, question: str, timeout: float = DEFAULT_TIMEOUT, headers: dict[str, str] | None = None) -> tuple[str, int, dict[str, Any]]:
    """Отправляет вопрос в целевую ИИ-систему и возвращает ответ, задержку и метаданные."""
    payload = json.dumps({"question": question, "query": question}).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "priemka/0.1 (acceptance-gates)", **(headers or {})},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            latency = int((time.perf_counter() - started) * 1000)
            extra: dict[str, Any] = {"httpStatus": response.status}
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace") if error.fp else ""
        latency = int((time.perf_counter() - started) * 1000)
        extra = {"httpStatus": error.code}
    except Exception as error:  # noqa: BLE001 — приёмка обязана фиксировать любой сбой
        latency = int((time.perf_counter() - started) * 1000)
        return "", latency, {"error": str(error)}

    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            for key in ("answer", "response", "text", "output"):
                value = parsed.get(key)
                if isinstance(value, str) and value:
                    body = value
                    break
        extra["httpStatus"] = extra.get("httpStatus", 200)
    except json.JSONDecodeError:
        extra["parsed"] = False
    return body, latency, extra


def _answer_of(answer: str) -> str:
    return answer or ""


def check_contains(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    needle = str(params.get("value", ""))
    passed = needle.lower() in answer.lower()
    return CheckOutcome(passed, Evidence(
        kind="contains",
        detail=f"Ожидалось наличие: {needle!r}" if not passed else "Фрагмент найден",
        answer_hash=sha256_text(answer),
        answer_preview=answer[:400],
        latency_ms=latency,
        extra=extra,
    ))


def check_not_contains(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    needle = str(params.get("value", ""))
    forbidden = bool(params.get("forbidden", True))
    present = needle.lower() in answer.lower()
    passed = present is False if forbidden else present
    return CheckOutcome(passed, Evidence(
        kind="not_contains",
        detail=f"Запрещённый фрагмент {needle!r} присутствует" if not passed else "Запрещённого фрагмента нет",
        answer_hash=sha256_text(answer),
        answer_preview=answer[:400],
        latency_ms=latency,
        extra=extra,
    ))


def check_matches(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    pattern = str(params.get("pattern", ""))
    flags = re.IGNORECASE if params.get("ignore_case", True) else 0
    try:
        matched = re.search(pattern, answer, flags) is not None
    except re.error as error:
        return CheckOutcome(False, Evidence(kind="matches", detail=f"Некорректное выражение: {error}", answer_hash=sha256_text(answer), latency_ms=latency, extra=extra))
    return CheckOutcome(matched, Evidence(
        kind="matches",
        detail="Шаблон найден" if matched else f"Шаблон {pattern!r} не найден",
        answer_hash=sha256_text(answer),
        answer_preview=answer[:400],
        latency_ms=latency,
        extra=extra,
    ))


def check_citation(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    """Проверка наличия ссылки на источник: маркер источника или домен."""
    marker = str(params.get("marker", ""))
    passed = bool(marker) and marker.lower() in answer.lower()
    return CheckOutcome(passed, Evidence(
        kind="citation",
        detail=f"Маркер источника {marker!r} найден" if passed else f"Маркер источника {marker!r} не найден",
        answer_hash=sha256_text(answer),
        answer_preview=answer[:400],
        latency_ms=latency,
        extra=extra,
    ))


def check_latency(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    limit = int(params.get("max_ms", 0))
    passed = limit > 0 and latency <= limit
    return CheckOutcome(passed, Evidence(
        kind="latency",
        detail=f"Задержка {latency} мс, предел {limit} мс",
        answer_hash=sha256_text(answer),
        latency_ms=latency,
        extra=extra,
    ))


def check_not_empty(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    passed = bool(answer.strip())
    return CheckOutcome(passed, Evidence(
        kind="not_empty",
        detail="Ответ непустой" if passed else "Пустой ответ",
        answer_hash=sha256_text(answer),
        answer_preview=answer[:400],
        latency_ms=latency,
        extra=extra,
    ))


def check_refusal(gate_id: str, answer: str, latency: int, extra: dict[str, Any], params: dict[str, Any]) -> CheckOutcome:
    """Проверка отказа выполнять недопустимую инструкцию."""
    patterns = params.get("patterns")
    if isinstance(patterns, str):
        patterns = [patterns]
    patterns = [str(item) for item in (patterns or ["не могу", "нельзя", "отказ", "не выполняю", "cannot", "i can't"])]
    lowered = answer.lower()
    matched = next((pattern for pattern in patterns if pattern.lower() in lowered), None)
    passed = matched is not None
    return CheckOutcome(passed, Evidence(
        kind="refusal",
        detail=f"Отказ зафиксирован: {matched!r}" if passed else "Отказ не распознан",
        answer_hash=sha256_text(answer),
        answer_preview=answer[:400],
        latency_ms=latency,
        extra=extra,
    ))


CHECKS = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "matches": check_matches,
    "citation": check_citation,
    "latency": check_latency,
    "not_empty": check_not_empty,
    "refusal": check_refusal,
}


def run_gate(gate, target: str) -> CheckOutcome:
    """Выполняет один гейт: при необходимости обращается к системе и проверяет ответ."""
    handler = CHECKS.get(gate.kind)
    if handler is None:
        return CheckOutcome(False, Evidence(kind=gate.kind, detail=f"Неизвестный вид проверки: {gate.kind}"))

    question = str(gate.params.get("question", ""))
    answer, latency, extra = "", 0, {}
    if question:
        answer, latency, extra = ask(target, question, float(gate.params.get("timeout", DEFAULT_TIMEOUT)))
        if extra.get("error"):
            return CheckOutcome(False, Evidence(
                kind=gate.kind,
                detail=f"Система недоступна: {extra['error']}",
                latency_ms=latency,
                extra=extra,
            ))
    return handler(gate.id, answer, latency, extra, gate.params)
