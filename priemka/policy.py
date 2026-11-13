"""Загрузка пакета проверок (TOML) и валидация.

Пакет описывает систему, гейты приёмки и критерии остановки. Схема намеренно
простая: TOML без зависимостей, читается стандартным tomllib.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PolicyError(ValueError):
    """Пакет проверок не проходит валидацию."""


@dataclass(frozen=True)
class Gate:
    """Один проверяемый гейт приёмки."""

    id: str
    kind: str
    description: str = ""
    severity: str = "blocking"
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        return self.severity == "blocking"


@dataclass(frozen=True)
class Pack:
    """Пакет проверок одной ИИ-системы."""

    name: str
    target: str
    description: str = ""
    stop_conditions: list[str] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)

    @property
    def blocking_gates(self) -> list[Gate]:
        return [gate for gate in self.gates if gate.blocking]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def load_pack(path: str | Path) -> Pack:
    """Читает TOML-пакет и проверяет обязательные поля."""
    source = Path(path)
    _require(source.is_file(), f"Пакет не найден: {source}")
    with open(source, "rb") as handle:
        raw = tomllib.load(handle)

    system = raw.get("system")
    _require(isinstance(system, dict), "Нет раздела [system]")
    name = system.get("name")
    target = system.get("target")
    _require(isinstance(name, str) and name.strip(), "Не задано system.name")
    _require(isinstance(target, str) and target.startswith("http"), "system.target должен быть http(s)-адресом")

    stop_conditions = raw.get("stop_conditions", [])
    _require(isinstance(stop_conditions, list), "stop_conditions должен быть списком")

    gates: list[Gate] = []
    seen: set[str] = set()
    for index, item in enumerate(raw.get("gates", [])):
        _require(isinstance(item, dict), f"Гейт #{index + 1} должен быть таблицей")
        gate_id = item.get("id")
        kind = item.get("kind")
        _require(isinstance(gate_id, str) and gate_id.strip(), f"У гейта #{index + 1} нет id")
        _require(gate_id not in seen, f"Дублирующийся id гейта: {gate_id}")
        _require(isinstance(kind, str) and kind.strip(), f"У гейта {gate_id} нет kind")
        seen.add(gate_id)
        params = {k: v for k, v in item.items() if k not in {"id", "kind", "description", "severity"}}
        severity = item.get("severity", "blocking")
        _require(severity in {"blocking", "advisory"}, f"Неизвестная severity у {gate_id}: {severity}")
        gates.append(Gate(
            id=gate_id,
            kind=kind,
            description=str(item.get("description", "")),
            severity=severity,
            params=params,
        ))

    _require(bool(gates), "В пакете нет ни одного гейта")
    return Pack(
        name=name,
        target=target,
        description=str(raw.get("description", "")),
        stop_conditions=[str(item) for item in stop_conditions],
        gates=gates,
    )
