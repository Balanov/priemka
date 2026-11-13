"""Командный интерфейс приёмки.

    priemka init                       — создать пакет проверок
    priemka rules                      — список видов проверок
    priemka explain <gate>             — что проверяет гейт и как чинить
    priemka run --pack pack.toml       — прогнать пакет и выпустить отчёт
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checks import CHECKS, DETERMINISTIC
from .policy import PolicyError, load_pack, starter_pack
from .report import render_console, render_markdown, verdict_of, write_report
from .runner import compare, run_pack
from .targets import build_target

GATE_DOCS = {
    "not_empty": ("Система отвечает", "quality", "Пустой ответ — система не работает или теряет результат."),
    "contains": ("Фрагмент присутствует в ответе", "quality", "Ожидаемый факт должен быть в ответе."),
    "not_contains": ("Запрещённого фрагмента нет", "safety", "Ловит утечку внутренних инструкций и данных."),
    "matches": ("Ответ совпадает с шаблоном", "quality", "Проверяет конкретность ответа: сроки, суммы, формат."),
    "citation": ("В ответе есть ссылка на источник", "quality", "Ответ без источника нельзя проверить."),
    "refusal": ("Система отказывает в недопустимом запросе", "safety", "Ловит выполнение инструкций по обходу правил."),
    "latency": ("Ответ укладывается в бюджет задержки", "performance", "Задержка важна там, где ответ идёт человеку в диалог."),
    "cost": ("Стоимость ответа в бюджете", "performance", "Контролирует стоимость эксплуатации."),
    "pii_leak": ("Персональных данных в ответе нет", "access", "Ловит доступ к данным без прав."),
    "grounded": ("Ответ опирается на заданный контекст", "quality", "Ответ должен быть выведен из источников."),
    "determinism": ("Повторный вопрос даёт тот же ответ", "reproducibility", "Нестабильность ломает доверие к результату."),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="priemka",
        description="Приёмка ИИ-систем: проверяемый допуск в эксплуатацию.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="создать пакет проверок")
    init.add_argument("--name", default="Моя ИИ-система")
    init.add_argument("--target", default="http://127.0.0.1:8000/ask")
    init.add_argument("--out", default="pack.toml")

    sub.add_parser("rules", help="список видов проверок")

    explain = sub.add_parser("explain", help="что проверяет гейт и как чинить")
    explain.add_argument("gate")

    run = sub.add_parser("run", help="прогнать пакет проверок")
    run.add_argument("--pack", required=True, help="путь к TOML-пакету")
    run.add_argument("--target", default=None, help="адрес проверяемой системы (перекрывает пакет)")
    run.add_argument("--fixture", default=None, help="записанные ответы вместо живого сервиса")
    run.add_argument("--baseline", default=None, help="базовая система для сравнения")
    run.add_argument("--baseline-fixture", default=None, help="фикстур базовой системы")
    run.add_argument("--out", default="reports", help="каталог для отчётов")
    run.add_argument("--json", action="store_true", help="печатать только JSON-отчёт")
    run.add_argument("--quiet", action="store_true", help="только код возврата")
    return parser


def cmd_init(args) -> int:
    path = Path(args.out)
    if path.exists():
        print(f"Файл уже существует: {path}", file=sys.stderr)
        return 2
    path.write_text(starter_pack(args.name, args.target), encoding="utf-8")
    print(f"Создан пакет проверок: {path}")
    print(f"Проверьте: priemka run --pack {path}")
    return 0


def cmd_rules(_args) -> int:
    print(f"{'вид':<14}{'измерение':<18}что проверяет")
    for kind, (title, dimension, note) in GATE_DOCS.items():
        print(f"{kind:<14}{dimension:<18}{title}")
        print(f"{'':<32}{note}")
    print()
    print("Код возврата: 0 — принято, 1 — есть проваленный блокирующий гейт, 2 — ошибка входных данных.")
    return 0


def cmd_explain(args) -> int:
    gate = args.gate
    if gate in GATE_DOCS:
        title, dimension, note = GATE_DOCS[gate]
        print(f"{gate} — {title}")
        print(f"измерение: {dimension}")
        print(f"что ловит: {note}")
        print()
        print("Пример в пакете:")
        print(f'  [[gates]]\n  id = "{gate}-example"\n  kind = "{gate}"')
        return 0
    known = ", ".join(sorted(GATE_DOCS))
    print(f"Неизвестный вид проверки: {gate}", file=sys.stderr)
    print(f"Доступные: {known}", file=sys.stderr)
    return 2


def cmd_run(args) -> int:
    try:
        pack = load_pack(args.pack)
    except PolicyError as error:
        print(f"Пакет проверок некорректен: {error}", file=sys.stderr)
        return 2

    target_url = args.target or pack.target
    try:
        target = build_target(target_url, args.fixture)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 2

    result = run_pack(pack, target)

    if args.baseline or args.baseline_fixture:
        try:
            baseline_target = build_target(args.baseline or target_url, args.baseline_fixture)
        except FileNotFoundError as error:
            print(str(error), file=sys.stderr)
            return 2
        compare(run_pack(pack, baseline_target), result)

    paths = write_report(result, args.out)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif not args.quiet:
        print(render_console(result))
        print()
        print(f"отчёт:    {paths['markdown']}")
        print(f"подпись:  {paths['sha256']}")

    return 0 if result.accepted else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "init": cmd_init,
        "rules": cmd_rules,
        "explain": cmd_explain,
        "run": cmd_run,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
