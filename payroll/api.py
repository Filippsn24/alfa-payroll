from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from payroll.calculator import calculate_payroll
from payroll.config import Settings, month_bounds, parse_month
from payroll.export import export_json, export_payroll_xlsx, export_tatyana_xlsx, payroll_to_dict
from payroll.tatyana import build_tatyana_report

app = FastAPI(
    title="ALFACRM Payroll API",
    description="Расчёт зарплаты тренеров из ALFACRM",
    version="1.0.0",
)


class ExtraItem(BaseModel):
    coach: str
    name: str
    qty: float = 1
    rate: float


class PayrollRequest(BaseModel):
    month: str = Field(..., description="Период в формате YYYY-MM, например 2026-05")
    extras: list[ExtraItem] = Field(default_factory=list)


def get_settings() -> Settings:
    return Settings.from_env()


def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    secret = settings.api_secret
    if not secret:
        return
    if x_api_key != secret:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/payroll", dependencies=[Depends(verify_api_key)])
def get_payroll(
    month: str = Query(..., description="YYYY-MM"),
    format: str = Query("json", pattern="^(json|xlsx)$"),
    tatyana: bool = Query(False, description="Добавить свод для Татьяны (только json)"),
    settings: Settings = Depends(get_settings),
) -> Any:
    year, mon = parse_month(month)
    date_from, date_to = month_bounds(year, mon)
    result = calculate_payroll(settings, date_from, date_to)

    if format == "json":
        payload = payroll_to_dict(result)
        if tatyana:
            rows, manual = build_tatyana_report(result)
            payload["tatyana"] = {"rows": rows, "manual": manual}
        return JSONResponse(payload)

    out_dir = os.environ.get("OUTPUT_DIR", "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"payroll_{month}.xlsx")
    export_payroll_xlsx(result, Path(path))
    return FileResponse(path, filename=f"payroll_{month}.xlsx")


@app.post("/payroll", dependencies=[Depends(verify_api_key)])
def post_payroll(
    body: PayrollRequest,
    format: str = Query("json", pattern="^(json|xlsx)$"),
    tatyana: bool = Query(False),
    settings: Settings = Depends(get_settings),
) -> Any:
    year, mon = parse_month(body.month)
    date_from, date_to = month_bounds(year, mon)
    extras = [item.model_dump() for item in body.extras]
    result = calculate_payroll(settings, date_from, date_to, extra_from_file=extras)

    if format == "json":
        payload = payroll_to_dict(result)
        if tatyana:
            rows, manual = build_tatyana_report(result)
            payload["tatyana"] = {"rows": rows, "manual": manual}
        return JSONResponse(payload)

    out_dir = os.environ.get("OUTPUT_DIR", "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"payroll_{body.month}.xlsx")
    export_payroll_xlsx(result, Path(path))
    return FileResponse(path, filename=f"payroll_{body.month}.xlsx")


@app.get("/tatyana", dependencies=[Depends(verify_api_key)])
def get_tatyana(
    month: str = Query(...),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    year, mon = parse_month(month)
    date_from, date_to = month_bounds(year, mon)
    result = calculate_payroll(settings, date_from, date_to)
    rows, manual = build_tatyana_report(result)
    return JSONResponse({"rows": rows, "manual": manual})


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("payroll.api:app", host="0.0.0.0", port=port, reload=False)
