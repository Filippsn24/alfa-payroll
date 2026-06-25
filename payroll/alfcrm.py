from __future__ import annotations

import re
import time
from typing import Any

import requests

from payroll.config import Settings
from payroll.rules import GROUP_ID_OVERRIDES


def normalize_text(value: str) -> str:
    value = (value or "").lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", value)


class AlfaCRMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self._token: str | None = None

    def login(self) -> str:
        resp = self.session.post(
            f"{self.settings.base_url}/v2api/auth/login",
            json={"email": self.settings.email, "api_key": self.settings.api_key},
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json().get("token")
        if not token:
            raise RuntimeError("ALFACRM login: token missing")
        self._token = token
        return token

    @property
    def token(self) -> str:
        if not self._token:
            return self.login()
        return self._token

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        time.sleep(0.2)
        headers = {"X-ALFACRM-TOKEN": self.token}
        resp = self.session.post(
            f"{self.settings.base_url}{path}",
            json=payload or {},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def paged_index(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 0
        while True:
            data = self.post(path, {"page": page})
            page_items = data.get("items") or []
            if not page_items:
                break
            items.extend(page_items)
            page += 1
        return items

    def fetch_teachers(self) -> dict[str, str]:
        path = f"/v2api/{self.settings.branch_id}/teacher/index"
        return {
            str(t["id"]): t.get("name") or f"Teacher #{t['id']}"
            for t in self.paged_index(path)
        }

    def fetch_groups(self) -> dict[str, str]:
        path = f"/v2api/{self.settings.branch_id}/group/index"
        return {
            str(g["id"]): g.get("name") or f"Group #{g['id']}"
            for g in self.paged_index(path)
        }

    def fetch_lessons(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        path = f"/v2api/{self.settings.branch_id}/lesson/index"
        first = self.post(
            path,
            {"page": 0, "status": 3, "date_from": date_from, "date_to": date_to},
        )
        total = int(first.get("total") or 0)
        pages = max(1, (total + 49) // 50)
        lessons: list[dict[str, Any]] = []
        for page in range(pages):
            data = first if page == 0 else self.post(
                path,
                {
                    "page": page,
                    "status": 3,
                    "date_from": date_from,
                    "date_to": date_to,
                },
            )
            lessons.extend(data.get("items") or [])
        return lessons


def pick_group_name(group_ids: list, groups_map: dict[str, str]) -> str:
    if not group_ids:
        return "Без группы"
    names: list[str] = []
    for gid in group_ids:
        gid_int = int(gid)
        if gid_int in GROUP_ID_OVERRIDES:
            names.append(GROUP_ID_OVERRIDES[gid_int])
        else:
            names.append(groups_map.get(str(gid), f"Group #{gid}"))
    return " | ".join(names)


def match_coach(crm_name: str, coach_order: list[str]) -> str | None:
    n = normalize_text(crm_name)
    for coach in coach_order:
        if normalize_text(coach) == n:
            return coach
    for coach in coach_order:
        full = normalize_text(coach)
        if full in n or n in full:
            return coach
    return None
