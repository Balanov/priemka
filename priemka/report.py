"""Отчёт приёмки: JSON, Markdown и подпись хешем.

Отчёт отвечает на вопрос заказчика: «можно ли эту систему принимать в эксплуатацию
и на что смотреть, если нельзя». Поэтому в нём есть вердикт, индекс готовности,
разбивка по измерениям и пошаговая подсказка по каждому проваленному гейту.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .runner import RunResult

VERDICT_MARKS = {
    "ПРИНЯТО": "ok",
    "ПРИНЯТО С ОГОВОРКАМИ": "warn",
    "НЕ ПРИНЯТО": "fail",
}


def verdict_of(result: RunResult) -> str:
    return result.grade


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_payload(result: RunResult) -> dict[str, Any]:
    """Часть отчёта, которая подписывается.

    Время прогона не входит в подпись: иначе два одинаковых прогона дали бы разные
    подписи и подпись перестала бы доказывать, что именно проверялось.
    """
    payload = result.to_dict()
    payload.pop("startedAt", None)
    payload.pop("finishedAt", None)
    return payload


def report_hash(payload: dict[str, Any]) -> str:
    """SHA-256 канонического отчёта — подпись, по которой отчёт можно сверить позже."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def payload_hash(result: RunResult) -> str:
    """Подпись результата прогона: без времени, только содержание проверок."""
    return report_hash(canonical_payload(result))


def verify_report(path: str | Path) -> dict[str, Any]:
    """Проверяет, что отчёт не менялся после подписания.

    Возвращает статус: `intact` — подпись сходится, `altered` — отчёт правили,
    `unsigned` — в отчёте нет подписи, `invalid` — файл не читается.
    """
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001
        return {"status": "invalid", "path": str(source), "error": str(error)}
    if not isinstance(payload, dict) or "reportSha256" not in payload:
        return {"status": "unsigned", "path": str(source)}
    stored = str(payload.pop("reportSha256"))
    payload.pop("startedAt", None)
    payload.pop("finishedAt", None)
    computed = report_hash(payload)
    return {
        "status": "intact" if computed == stored else "altered",
        "path": str(source),
        "stored": stored,
        "computed": computed,
    }


def _bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 100 * width))
    return "█" * filled + "·" * (width - filled)


def render_markdown(result: RunResult) -> str:
    """Человекочитаемый отчёт приёмки."""
    payload = result.to_dict()
    verdict = verdict_of(result)
    mark = VERDICT_MARKS.get(verdict, "fail")
    lines = [
        f"# Приёмка: {result.pack.name}",
        "",
        f"**Вердикт:** {verdict}",
        f"**Индекс готовности:** {result.score:.1f} / 100  `{_bar(result.score)}`",
        f"**Проверено гейтов:** {payload['gatesPassed']} из {payload['gatesTotal']}",
        f"**Цель:** {result.target}",
        f"**Прогон:** {result.started_at} → {result.finished_at}",
        "",
    ]
    if result.pack.description:
        lines += [result.pack.description, ""]

    lines += ["## Измерения", "", "| Измерение | Оценка | Гейтов |", "|---|---:|---:|"]
    for dimension, data in result.dimensions().items():
        lines.append(f"| {data['label']} | {data['score']:.0f} / 100 | {data['passed']} / {data['total']} |")
    lines += [""]

    if result.regressions:
        lines += ["## Регрессии относительно базовой системы", ""]
        for item in result.regressions:
            lines.append(f"- `{item.id}`: базовая система проходила, текущая — нет. {item.detail}")
        lines += [""]

    lines += ["## Гейты", "", "| Гейт | Измерение | Важность | Итог | Комментарий |", "|---|---|---|---|---|"]
    for item in result.outcomes:
        state = "пройден" if item.passed else "НЕ ПРОЙДЕН"
        lines.append(f"| `{item.id}` | {item.gate.dimension_label} | {item.gate.severity} | {state} | {item.detail} |")
    lines += [""]

    failures = [item for item in result.outcomes if not item.passed]
    if failures:
        lines += ["## Что чинить", ""]
        for item in failures:
            lines.append(f"### `{item.id}` — {item.gate.description or item.gate.kind}")
            lines.append("")
            lines.append(f"- **Проблема:** {item.detail}")
            if item.fix:
                lines.append(f"- **Что сделать:** {item.fix}")
            evidence = item.evidence or {}
            if evidence.get("answerPreview"):
                lines.append(f"- **Что ответила система:** {evidence['answerPreview'][:220]}")
            if evidence.get("answerSha256"):
                lines.append(f"- **Хеш ответа (SHA-256):** `{evidence['answerSha256']}`")
            lines.append("")

    if result.pack.stop_conditions:
        lines += ["## Условия остановки", ""]
        lines += [f"- {item}" for item in result.pack.stop_conditions]
        lines += [""]

    lines += [
        "---",
        "",
        f"Подпись отчёта (SHA-256): `{report_hash(payload)}`",
        "",
        "Отчёт подтверждает состояние системы на момент прогона. Он не заменяет приёмку "
        "человеком, ответственным за эксплуатацию, и не является гарантией качества.",
    ]
    return "\n".join(lines)


def render_console(result: RunResult) -> str:
    """Короткая сводка для терминала и для CI-лога."""
    verdict = verdict_of(result)
    lines = [
        f"система: {result.pack.name}",
        f"цель:    {result.target}",
        f"вердикт: {verdict}",
        f"готовность: {result.score:.1f}/100",
        "",
    ]
    for item in result.outcomes:
        state = "ok  " if item.passed else "FAIL"
        lines.append(f"  [{state}] {item.id:<28} {item.detail}")
    if result.failed_blocking:
        lines.append("")
        lines.append(f"блокирующих гейтов не пройдено: {len(result.failed_blocking)} — система не принята")
    if result.regressions:
        lines.append(f"регрессий к базовой системе: {len(result.regressions)}")
    return "\n".join(lines)


def write_report(result: RunResult, out_dir: str | Path) -> dict[str, str]:
    """Пишет JSON и Markdown отчёты, возвращает пути и хеш."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    digest = payload_hash(result)
    payload["reportSha256"] = digest

    json_path = directory / "acceptance-report.json"
    md_path = directory / "acceptance-report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "sha256": digest,
    }
