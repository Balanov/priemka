"""Цели проверки: живой HTTP-сервис или записанный фикстур.

Фикстур делает прогон воспроизводимым и офлайновым: демонстрация, CI и
регрессионные тесты не зависят от доступности модели.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Answer:
    """Ответ проверяемой системы."""

    text: str
    latency_ms: int = 0
    tokens: int | None = None
    cost: float | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return self.error is not None


class Target:
    """Базовый класс цели."""

    name = "target"

    def ask(self, question: str) -> Answer:
        raise NotImplementedError

    def describe(self) -> str:
        return self.name


class HttpTarget(Target):
    """Живая система: POST с вопросом, ответ в JSON."""

    name = "http"

    def __init__(self, url: str, timeout: float = 30.0, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}

    def describe(self) -> str:
        return self.url

    def ask(self, question: str) -> Answer:
        payload = json.dumps({"question": question, "query": question}).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "priemka/1.0 (acceptance-gates)",
                **self.headers,
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace") if error.fp else ""
            return Answer(
                text=body,
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=f"HTTP {error.code}",
                meta={"httpStatus": error.code},
            )
        except Exception as error:  # noqa: BLE001 — приёмка обязана фиксировать любой сбой
            return Answer(
                text="",
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=str(error),
            )

        latency = int((time.perf_counter() - started) * 1000)
        meta: dict[str, Any] = {"httpStatus": status}
        tokens: int | None = None
        cost: float | None = None
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                tokens = parsed.get("tokens") or (parsed.get("usage") or {}).get("total_tokens")
                cost = parsed.get("cost")
                for key in ("answer", "response", "text", "output", "content"):
                    value = parsed.get(key)
                    if isinstance(value, str) and value:
                        body = value
                        break
        except json.JSONDecodeError:
            meta["parsed"] = False
        return Answer(text=body, latency_ms=latency, tokens=tokens, cost=cost, meta=meta)


class FixtureTarget(Target):
    """Записанные ответы: прогон без сети и без модели."""

    name = "fixture"

    def __init__(self, path: str | Path | dict) -> None:
        if isinstance(path, dict):
            raw = path
            self.path = None
        else:
            source = Path(path)
            if not source.is_file():
                raise FileNotFoundError(f"Фикстур не найден: {source}")
            raw = json.loads(source.read_text(encoding="utf-8"))
            self.path = source
        self.answers: dict[str, dict[str, Any]] = {}
        for entry in raw.get("answers", []):
            self.answers[entry["question"]] = entry
        self.default = raw.get("default")
        self.latency_ms = int(raw.get("latency_ms", 120))

    def describe(self) -> str:
        return f"fixture:{self.path.name}" if self.path else "fixture:inline"

    def ask(self, question: str) -> Answer:
        entry = self.answers.get(question)
        if entry is None:
            entry = self.default
        if entry is None:
            return Answer(text="", latency_ms=self.latency_ms, error=f"нет записи для вопроса: {question[:60]}")
        return Answer(
            text=str(entry.get("answer", "")),
            latency_ms=int(entry.get("latency_ms", self.latency_ms)),
            tokens=entry.get("tokens"),
            cost=entry.get("cost"),
            meta={"fixture": True},
        )


def build_target(target: str, fixture: str | None = None) -> Target:
    """Выбирает цель проверки: фикстур, если задан, иначе живой HTTP."""
    if fixture:
        return FixtureTarget(fixture)
    return HttpTarget(target)
