from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from payroll.alfcrm import AlfaCRMClient, match_coach, normalize_text, pick_group_name
from payroll.config import Settings
from payroll.rules import (
    BUILTIN_EXTRA_NAMES,
    COACH_ORDER,
    CUSTOM_200_GROUPS,
    EXTRA_FIXED,
    KUBOK_METEOR_KIDS,
    KUBOK_RATE,
    KUKOROVA_RATE,
)


@dataclass
class PayrollLine:
    name: str
    qty: float
    rate: float

    @property
    def amount(self) -> float:
        return self.qty * self.rate


@dataclass
class CoachBlock:
    coach: str
    groups: list[PayrollLine] = field(default_factory=list)
    extras: list[PayrollLine] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(line.amount for line in self.groups + self.extras)


@dataclass
class PayrollResult:
    date_from: str
    date_to: str
    coaches: list[CoachBlock]
    grand_total: float
    lesson_count: int


def is_kukorova(coach: str) -> bool:
    return "кукорова" in normalize_text(coach)


def resolve_rate(coach: str, group_name: str, attended_kids: int) -> int:
    n_coach = normalize_text(coach)
    n_group = normalize_text(group_name)

    if "кузнецов" in n_coach:
        return 140
    if "андронов" in n_coach:
        if "фш" in n_group:
            return 230
        if "фс" in n_group:
            return 150
        return 100

    for marker in CUSTOM_200_GROUPS.get(coach, []):
        m = normalize_text(marker)
        if m and m in n_group:
            return 200
    return 100


def get_extra_fixed_rows(coach: str) -> list[PayrollLine]:
    rows: list[PayrollLine] = []
    for item in EXTRA_FIXED.get(coach, []):
        rows.append(PayrollLine(item["name"], item["qty"], item["rate"]))
    kids = KUBOK_METEOR_KIDS.get(coach, 0)
    if kids and kids > 0:
        rows.append(PayrollLine("Кубок Метеора", kids, KUBOK_RATE))
    return rows


def filter_sheet_extras(
    sheet_rows: list[PayrollLine], fixed_rows: list[PayrollLine]
) -> list[PayrollLine]:
    fixed_names = {normalize_text(r.name) for r in fixed_rows}
    out: list[PayrollLine] = []
    for row in sheet_rows:
        n = normalize_text(row.name)
        if n in BUILTIN_EXTRA_NAMES:
            continue
        if n in fixed_names:
            continue
        out.append(row)
    return out


def calculate_payroll(
    settings: Settings,
    date_from: str,
    date_to: str,
    extra_from_file: list[dict[str, Any]] | None = None,
) -> PayrollResult:
    client = AlfaCRMClient(settings)
    client.login()
    teachers = client.fetch_teachers()
    groups = client.fetch_groups()
    lessons = client.fetch_lessons(date_from, date_to)

    extra_by_coach: dict[str, list[PayrollLine]] = {}
    for item in extra_from_file or []:
        coach = item.get("coach") or ""
        if not coach:
            continue
        extra_by_coach.setdefault(coach, []).append(
            PayrollLine(
                str(item.get("name", "")),
                float(item.get("qty", 0)),
                float(item.get("rate", 0)),
            )
        )

    # Accumulate per coach
    raw: dict[str, dict[str, Any]] = {
        coach: {"depts": {}, "min5": 0, "lessons": 0} for coach in COACH_ORDER
    }

    for lesson in lessons:
        details = lesson.get("details") or []
        attend = sum(1 for d in details if d.get("is_attend") == 1)
        group_name = pick_group_name(lesson.get("group_ids") or [], groups)

        for tid in lesson.get("teacher_ids") or []:
            crm_name = teachers.get(str(tid), "")
            coach = match_coach(crm_name, COACH_ORDER)
            if not coach:
                continue

            block = raw[coach]
            block["lessons"] += 1

            if is_kukorova(coach):
                dept = block["depts"].setdefault(group_name, {"lessons": 0})
                dept["lessons"] += 1
                continue

            rate = resolve_rate(coach, group_name, attend)
            dept = block["depts"].setdefault(group_name, {"kids": 0, "rate": rate})
            dept["kids"] += attend
            dept["rate"] = rate

            if rate == 100 and 0 < attend < 5:
                block["min5"] += 5 - attend

    coaches: list[CoachBlock] = []
    for coach in COACH_ORDER:
        block = raw[coach]
        coach_block = CoachBlock(coach=coach)

        for dept_name in sorted(block["depts"].keys()):
            v = block["depts"][dept_name]
            if is_kukorova(coach):
                coach_block.groups.append(
                    PayrollLine(dept_name, v.get("lessons", 0), KUKOROVA_RATE)
                )
            else:
                coach_block.groups.append(
                    PayrollLine(dept_name, v.get("kids", 0), v.get("rate", 100))
                )

        if not is_kukorova(coach) and block["min5"] > 0:
            coach_block.extras.append(PayrollLine("Меньше 5 детей", block["min5"], 100))

        fixed = get_extra_fixed_rows(coach)
        coach_block.extras.extend(fixed)
        coach_block.extras.extend(
            filter_sheet_extras(extra_by_coach.get(coach, []), fixed)
        )

        coaches.append(coach_block)

    grand = sum(c.total for c in coaches)
    return PayrollResult(
        date_from=date_from,
        date_to=date_to,
        coaches=coaches,
        grand_total=grand,
        lesson_count=len(lessons),
    )
