#!/usr/bin/env python3
"""Измерения приёмки: накладные расходы, детерминированность, объём отчёта.

Запуск:
    python bench/benchmark.py --out bench/results/windows-cpython.json

Результат — сырой JSON с параметрами окружения, чтобы цифры можно было
перепроверить на другой машине.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from priemka.policy import load_pack  # noqa: E402
from priemka.report import report_hash, render_markdown, write_report  # noqa: E402
from priemka.runner import run_pack  # noqa: E402
from priemka.targets import FixtureTarget  # noqa: E402

PACK = ROOT / "examples" / "pack-rag.toml"
FIXTURE = ROOT / "examples" / "fixture-rag.json"
REPEAT = 25


def measure_run() -> dict:
    pack = load_pack(PACK)
    target = FixtureTarget(FIXTURE)
    timings = []
    for _ in range(REPEAT):
        started = time.perf_counter()
        result = run_pack(pack, target)
        timings.append((time.perf_counter() - started) * 1000)
    return {
        "gates": len(result.outcomes),
        "repeat": REPEAT,
        "meanMs": round(statistics.fmean(timings), 3),
        "medianMs": round(statistics.median(timings), 3),
        "minMs": round(min(timings), 3),
        "maxMs": round(max(timings), 3),
        "stdevMs": round(statistics.pstdev(timings), 3) if len(timings) > 1 else 0.0,
    }


def measure_report() -> dict:
    pack = load_pack(PACK)
    result = run_pack(pack, FixtureTarget(FIXTURE))
    digests = []
    sizes = []
    for _ in range(5):
        payload = result.to_dict()
        payload["startedAt"] = ""
        payload["finishedAt"] = ""
        digests.append(report_hash(payload))
        sizes.append(len(render_markdown(result).encode("utf-8")))
    return {
        "repeat": 5,
        "stableDigest": len(set(digests)) == 1,
        "digest": digests[0],
        "markdownBytes": sizes[0],
    }


def measure_payload() -> dict:
    raw = FIXTURE.read_bytes()
    return {
        "fixtureBytes": len(raw),
        "fixtureSha256": hashlib.sha256(raw).hexdigest(),
        "packSha256": hashlib.sha256(PACK.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "bench" / "results" / "local.json"))
    args = parser.parse_args()

    payload = {
        "tool": "priemka",
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "measurements": {
            "run": measure_run(),
            "report": measure_report(),
            "inputs": measure_payload(),
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
