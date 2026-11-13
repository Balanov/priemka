"""Отчёт приёмки: JSON, Markdown и подпись хешем."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .runner import RunResult


def verdict_of(result: RunResult) -> str:
    """Вердикт приёмки. Fail-closed: любой проваленный блокирующий гейт означает отказ."""
    return "ПРИНЯТО" if result.accepted else "НЕ ПРИНЯТО"


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def report_hash(payload: dict[str, Any]) -> str:
    """SHA-256 канонического отчёта — подпись, по которой отчёт можно сверить позже."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def render_markdown(result: RunResult) -> str:
    """Человекочитаемый отчёт приёмки."""
    payload = result.to_dict()
    lines = [
        f"# Приёмка: {result.pack.name}",
        "",
        f"**Вердикт:** {verdict_of(result)}",
        f"**Проверено гейтов:** {payload['gatesPassed']} из {payload['gatesTotal']}",
        f"**Цель:** {result.pack.target}",
        f"**Прогон:** {result.started_at} → {result.finished_at}",
        "",
    ]
    if result.pack.description:
        lines += [result.pack.description, ""]
    if result.pack.stop_conditions:
        lines += ["## Условия остановки", ""]
        lines += [f"- {item}" for item in result.pack.stop_conditions]
        lines += [""]
    lines += ["## Гейты", "", "| Гейт | Вид | Важность | Итог | Доказательство |", "|---|---|---|---|---|"]
    for item in result.results:
        mark = "пройден" if item.passed else "не пройден"
        lines.append(f"| {item.id} | {item.kind} | {item.severity} | {mark} | {item.detail} |")
    lines += ["", "## Доказательства", ""]
    for item in result.results:
        evidence = item.evidence or {}
        lines.append(f"### {item.id} — {'пройден' if item.passed else 'не пройден'}")
        lines.append("")
        lines.append(f"- Ответ (SHA-256): `{evidence.get('answerSha256', '—')}`")
        if evidence.get("latencyMs") is not None:
            lines.append(f"- Задержка: {evidence['latencyMs']} мс")
        if evidence.get("answerPreview"):
            lines.append(f"- Фрагмент ответа: {evidence['answerPreview'][:240]}")
        lines.append(f"- Комментарий: {item.detail}")
        lines.append("")
    lines += [
        "---",
        "",
        f"Подпись отчёта (SHA-256): `{report_hash(payload)}`",
        "",
        "Отчёт подтверждает состояние системы на момент прогона и не заменяет приёмку "
        "человеком ответственным за эксплуатацию.",
    ]
    return "\n".join(lines)


def write_report(result: RunResult, out_dir: str | Path) -> dict[str, str]:
    """Пишет JSON и Markdown отчёты, возвращает пути и хеш."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    digest = report_hash(payload)
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
