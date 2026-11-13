"""Командный интерфейс приёмки.

    python -m priemka run --pack packs/rag-enterprise.toml --out reports/
    python -m priemka check --pack packs/rag-enterprise.toml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .policy import PolicyError, load_pack
from .report import verdict_of, write_report
from .runner import run_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="priemka",
        description="Приёмка ИИ-систем: проверяемый допуск в эксплуатацию.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="прогнать пакет проверок и выпустить отчёт")
    run.add_argument("--pack", required=True, help="путь к TOML-пакету проверок")
    run.add_argument("--out", default="reports", help="каталог для отчётов")
    run.add_argument("--json", action="store_true", help="печатать только JSON-отчёт")

    check = sub.add_parser("check", help="только проверить корректность пакета")
    check.add_argument("--pack", required=True, help="путь к TOML-пакету проверок")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pack = load_pack(args.pack)
    except PolicyError as error:
        print(f"Пакет проверок некорректен: {error}", file=sys.stderr)
        return 2

    if args.command == "check":
        print(f"Пакет корректен: {pack.name}")
        print(f"Гейтов: {len(pack.gates)} (блокирующих: {len(pack.blocking_gates)})")
        print(f"Цель: {pack.target}")
        return 0

    result = run_pack(pack)
    paths = write_report(result, args.out)

    if args.json:
        import json
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Система: {pack.name}")
        print(f"Вердикт: {verdict_of(result)}")
        for item in result.results:
            mark = "пройден" if item.passed else "НЕ ПРОЙДЕН"
            print(f"  [{mark}] {item.id}: {item.detail}")
        if result.failed_blocking:
            print("\nБлокирующие гейты не пройдены — система не принята в эксплуатацию.")
        print(f"\nОтчёт: {paths['markdown']}")
        print(f"Подпись (SHA-256): {paths['sha256']}")

    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
