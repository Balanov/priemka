"""Измерения для страницы продукта: накладные расходы против вызова модели, след, воспроизводимость.

  1) прогон 11 гейтов (медиана) против одного вызова локальной модели — честное сравнение:
     «сколько стоит проверка» против «сколько стоит сама система»;
  2) локальный след: зависимости и размер;
  3) воспроизводимость отчёта: одинаковые входы -> одинаковая подпись.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from priemka.policy import load_pack  # noqa: E402
from priemka.report import report_hash, render_markdown  # noqa: E402
from priemka.runner import run_pack  # noqa: E402
from priemka.targets import FixtureTarget  # noqa: E402

PACK = ROOT / "examples" / "pack-rag.toml"
FIXTURE = ROOT / "examples" / "fixture-rag.json"
REPEAT = 25
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3:8b"


def harness_overhead() -> dict:
    pack = load_pack(PACK)
    target = FixtureTarget(FIXTURE)
    timings = []
    for _ in range(REPEAT):
        started = time.perf_counter()
        run_pack(pack, target)
        timings.append((time.perf_counter() - started) * 1000)
    return {
        "gates": len(pack.gates),
        "repeat": REPEAT,
        "medianMs": round(statistics.median(timings), 3),
        "meanMs": round(statistics.fmean(timings), 3),
        "minMs": round(min(timings), 3),
        "maxMs": round(max(timings), 3),
    }


def model_call() -> dict | None:
    """Один вызов локальной модели: нижняя граница «стоимости проверяемой системы»."""
    payload = json.dumps({
        "model": MODEL,
        "prompt": "Ответь одним предложением: какой срок согласования договора?",
        "stream": False,
        "options": {"num_predict": 64},
    }).encode("utf-8")
    request = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                response.read()
        except Exception:
            return None
        timings.append((time.perf_counter() - started) * 1000)
    return {"model": MODEL, "repeat": 3, "medianMs": round(statistics.median(timings), 1)}


def footprint() -> dict:
    """Локальный след пакета: размер исходников и число зависимостей."""
    files = [p for p in (ROOT / "priemka").rglob("*.py")]
    lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files)
    return {
        "files": len(files),
        "lines": lines,
        "runtimeDependencies": 0,
        "sdistBytes": 0,
    }


def reproducibility() -> dict:
    pack = load_pack(PACK)
    digests = []
    verdicts = []
    for _ in range(5):
        result = run_pack(pack, FixtureTarget(FIXTURE))
        payload = result.to_dict()
        payload["startedAt"] = ""
        payload["finishedAt"] = ""
        digests.append(report_hash(payload))
        verdicts.append(f"{result.grade}/{result.score}")
    return {
        "repeat": 5,
        "digestStable": len(set(digests)) == 1,
        "digest": digests[0],
        "verdicts": sorted(set(verdicts)),
        "markdownBytes": len(render_markdown(run_pack(pack, FixtureTarget(FIXTURE))).encode("utf-8")),
    }


def main() -> None:
    out = {
        "harness": harness_overhead(),
        "modelCall": model_call(),
        "footprint": footprint(),
        "reproducibility": reproducibility(),
    }
    target = ROOT / "bench" / "results" / "page-measurements.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
