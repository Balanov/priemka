"""Измеряет след установки инструментов оценки, с которыми сравнивается `priemka`.

Зачем это здесь: страница и README утверждают, что `priemka` не тянет ни одной
runtime-зависимости. Утверждение о конкурентах («у них judge-метрики, то есть
вызовы модели») проверяется рассуждением, а утверждение о размере следа —
измерением. Этот скрипт даёт оба числа и повторяется на любой машине.

Примеры:

    python bench/compare_footprint.py
    python bench/compare_footprint.py --tree ragas
    python bench/compare_footprint.py --package priemka

`--tree` скачивает пакет вместе со всеми зависимостями — это то, что реально
занимает место на диске. `--no-deps` (по умолчанию) меряет только верхний
уровень и честно это оговаривает в выводе.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGES = [
    ("deepEval", "DeepEval"),
    ("promptfoo", "promptfoo"),
    ("ragas", "Ragas"),
    ("giskard", "Giskard"),
    ("priemka", "PRIEMKA"),
]


def measure(package: str, tree: bool, dest: Path) -> tuple[int, int]:
    """Возвращает (число файлов, суммарный размер в байтах)."""
    target = dest / package
    target.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "download", "--quiet", "--dest", str(target)]
    if not tree:
        cmd.append("--no-deps")
    cmd.append(package)
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    files = [p for p in target.iterdir() if p.is_file()]
    if done.returncode != 0 and not files:
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        raise RuntimeError(detail[-1] if detail else f"pip download {package} failed")
    return len(files), sum(p.stat().st_size for p in files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="append", default=[], help="измерить только этот пакет")
    parser.add_argument("--tree", default="", help="дополнительно измерить пакет со всеми зависимостями")
    parser.add_argument("--no-deps", dest="no_deps", action="store_true", default=True,
                        help="(по умолчанию) только верхний уровень, без дерева зависимостей")
    args = parser.parse_args()

    wanted = {p.lower() for p in args.package} if args.package else None
    root = Path(tempfile.mkdtemp(prefix="priemka-footprint-"))
    try:
        rows = []
        for package, label in PACKAGES:
            if wanted and package.lower() not in wanted:
                continue
            try:
                count, size = measure(package, False, root)
                rows.append((label, count, size, "верхний уровень"))
            except RuntimeError as error:
                print(f"{label}: не измерить — {error}")
        if args.tree:
            try:
                count, size = measure(args.tree, True, root)
                rows.append((args.tree, count, size, "с деревом зависимостей"))
            except RuntimeError as error:
                print(f"{args.tree}: не измерить — {error}")

        if not rows:
            print("нечего показывать")
            return 1

        width = max(len(r[0]) for r in rows)
        print()
        print(f"{'пакет'.ljust(width)}  {'файлов':>7}  {'размер':>14}  что меряли")
        print("-" * (width + 40))
        for label, count, size, what in rows:
            print(f"{label.ljust(width)}  {count:>7}  {size:>13,} Б  {what}")
        print()
        print("Верхний уровень — wheel самого пакета без дерева зависимостей.")
        print("Чтобы сравнить реальный след на диске, измерьте с --tree.")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
