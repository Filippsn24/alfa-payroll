from __future__ import annotations

import json
from pathlib import Path

from payroll.alfcrm import normalize_text
from payroll.calculator import CoachBlock, PayrollLine, PayrollResult
from payroll.config import DATA_DIR
from payroll.rules import ARTICLE, COACH_ORDER, PROJECT_KUBOK, PROJECT_LAGER_1474


def load_group_project_map() -> list[dict[str, str]]:
    path = DATA_DIR / "group_project_pairs.json"
    pairs = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"project": p, "group": g, "ng": normalize_text(g)} for p, g in pairs
    ]


def match_project(group_name: str, project_map: list[dict[str, str]]) -> str | None:
    n = normalize_text(group_name)
    if not n:
        return None
    for item in project_map:
        if item["ng"] == n:
            return item["project"]
    best = None
    best_len = 0
    for item in project_map:
        p = item["ng"]
        if not p:
            continue
        if p in n or n in p:
            if len(p) > best_len:
                best_len = len(p)
                best = item["project"]
    return best


def is_sbornaya_group_name(n: str) -> bool:
    return (
        "сборн" in n
        or "сбиг" in n
        or "сбпр" in n
        or "плюс" in n
        or "pro" in n
        or "суббот" in n
        or ("сб" in n and "сборн" not in n)
    )


def is_sbornaya_project_code(code: str) -> bool:
    c = normalize_text(code)
    return "сбор" in c or "сб" in c or "игр" in c


def has_project_1474(group_projects: list[str], groups: list[PayrollLine]) -> bool:
    for p in group_projects:
        if "1474" in str(p):
            return True
    for g in groups:
        if "1474" in g.name:
            return True
    return False


def pick_any_project(by_project: dict[str, float], group_projects: list[str]) -> str | None:
    if not by_project:
        return group_projects[0] if group_projects else None
    return max(by_project.items(), key=lambda x: x[1])[0]


def pick_sbornaya_project(
    groups: list[PayrollLine],
    by_project: dict[str, float],
    project_map: list[dict[str, str]],
) -> str | None:
    for g in groups:
        gn = normalize_text(g.name)
        if is_sbornaya_group_name(gn):
            p = match_project(g.name, project_map)
            if p:
                return p
    for code in by_project:
        if is_sbornaya_project_code(code):
            return code
    return None


def distribute_extra(
    coach: str,
    extra: PayrollLine,
    by_project: dict[str, float],
    group_projects: list[str],
    groups: list[PayrollLine],
    manual_rows: list[list],
    project_map: list[dict[str, str]],
) -> None:
    amount = extra.amount
    if not amount:
        return
    n = normalize_text(extra.name)

    if "кубокметеора" in n:
        by_project[PROJECT_KUBOK] = by_project.get(PROJECT_KUBOK, 0) + amount
        return

    if "меньше5" in n:
        proj = pick_any_project(by_project, group_projects)
        if proj:
            by_project[proj] = by_project.get(proj, 0) + amount
        return

    if "фиксзасборную" in n:
        sb = pick_sbornaya_project(groups, by_project, project_map)
        if sb:
            by_project[sb] = by_project.get(sb, 0) + amount
        else:
            manual_rows.append([coach, ARTICLE, "Фикс за сборную (нет сборной)", amount])
        return

    if "лагерь" in n:
        if has_project_1474(group_projects, groups):
            by_project[PROJECT_LAGER_1474] = by_project.get(PROJECT_LAGER_1474, 0) + amount
        else:
            manual_rows.append([coach, ARTICLE, "Лагерь (проект не задан, напр. 771)", amount])
        return

    if "лидогенерация" in n or "турнирдесятка" in n:
        manual_rows.append([coach, ARTICLE, extra.name, amount])
        return

    manual_rows.append([coach, ARTICLE, extra.name, amount])


def build_tatyana_report(result: PayrollResult) -> tuple[list[list], list[list]]:
    project_map = load_group_project_map()
    out_rows: list[list] = []
    manual_rows: list[list] = []

    for coach in COACH_ORDER:
        block = next((c for c in result.coaches if c.coach == coach), None)
        if not block:
            continue

        by_project: dict[str, float] = {}
        group_projects: list[str] = []

        for line in block.groups:
            proj = match_project(line.name, project_map)
            if not proj:
                manual_rows.append([coach, ARTICLE, f"НЕ НАЙДЕН ПРОЕКТ: {line.name}", line.amount])
                continue
            by_project[proj] = by_project.get(proj, 0) + line.amount
            if proj not in group_projects:
                group_projects.append(proj)

        for extra in block.extras:
            distribute_extra(
                coach, extra, by_project, group_projects, block.groups, manual_rows, project_map
            )

        for proj in sorted(by_project):
            out_rows.append([coach, ARTICLE, proj, by_project[proj]])

    return out_rows, manual_rows
