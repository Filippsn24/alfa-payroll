"""CLI: python -m payroll --month 2026-05"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from payroll.calculator import calculate_payroll
from payroll.config import PROJECT_ROOT, Settings, month_bounds, parse_month
from payroll.export import export_json, export_payroll_xlsx, export_tatyana_xlsx
from payroll.tatyana import build_tatyana_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Расчёт зарплаты тренеров ALFACRM")
    parser.add_argument("--month", required=True, help="Период YYYY-MM, например 2026-05")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "output"),
        help="Папка для xlsx/json",
    )
    parser.add_argument(
        "--extras",
        help="JSON-файл с доп.расходами: [{coach, name, qty, rate}, ...]",
    )
    parser.add_argument("--json", action="store_true", help="Сохранить JSON")
    parser.add_argument("--tatyana", action="store_true", help="Свод для Татьяны (xlsx)")
    parser.add_argument("--api", action="store_true", help="Запустить HTTP API")
    args = parser.parse_args(argv)

    if args.api:
        from payroll.api import main as run_api

        run_api()
        return 0

    year, mon = parse_month(args.month)
    date_from, date_to = month_bounds(year, mon)
    settings = Settings.from_env()

    extras = None
    if args.extras:
        extras = json.loads(Path(args.extras).read_text(encoding="utf-8"))

    print(f"Расчёт за {date_from} — {date_to}...")
    result = calculate_payroll(settings, date_from, date_to, extra_from_file=extras)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    xlsx_path = out / f"payroll_{args.month}.xlsx"
    export_payroll_xlsx(result, xlsx_path)
    print(f"Зарплата: {xlsx_path} (итого {result.grand_total:,.0f} руб.)")

    if args.json:
        json_path = out / f"payroll_{args.month}.json"
        export_json(result, json_path)
        print(f"JSON: {json_path}")

    if args.tatyana:
        rows, manual = build_tatyana_report(result)
        tat_path = out / f"tatyana_{args.month}.xlsx"
        export_tatyana_xlsx(rows, manual, tat_path)
        print(f"Татьяна: {tat_path} ({len(rows)} строк, {len(manual)} ручных)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
