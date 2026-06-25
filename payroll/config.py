from __future__ import annotations

import calendar
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class Settings:
    base_url: str
    branch_id: int
    email: str
    api_key: str
    api_secret: str | None

    @classmethod
    def from_env(cls) -> Settings:
        email = os.environ.get("ALFACRM_EMAIL", "")
        api_key = os.environ.get("ALFACRM_API_KEY", "")
        if not email or not api_key:
            raise ValueError(
                "Set ALFACRM_EMAIL and ALFACRM_API_KEY in .env or environment"
            )
        return cls(
            base_url=os.environ.get("ALFACRM_BASE_URL", "https://meteor.s20.online").rstrip("/"),
            branch_id=int(os.environ.get("ALFACRM_BRANCH_ID", "1")),
            email=email,
            api_key=api_key,
            api_secret=os.environ.get("PAYROLL_API_KEY"),
        )


def month_bounds(year: int, month: int) -> tuple[str, str]:
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def parse_month(value: str) -> tuple[int, int]:
    """Parse YYYY-MM or YYYY-M."""
    parts = value.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid month format: {value!r}. Use YYYY-MM")
    return int(parts[0]), int(parts[1])
