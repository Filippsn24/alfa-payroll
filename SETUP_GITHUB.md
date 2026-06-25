# ALFACRM Payroll

Репозиторий: https://github.com/Filippsn24/alfa-payroll

Автоматический расчёт зарплаты тренеров по футболу из [ALFACRM](https://meteor.s20.online).

## Быстрый старт

```powershell
cd alfa-payroll
copy .env.example .env
pip install -r requirements.txt
python -m payroll --month 2026-05 --json --tatyana
```

## GitHub Actions

1. **Settings → Secrets → Actions** — добавьте `ALFACRM_EMAIL` и `ALFACRM_API_KEY`
2. **Actions → Calculate Payroll → Run workflow**

## API

```powershell
python -m payroll --api
# GET http://localhost:8000/payroll?month=2026-05
```

Подробнее — см. [README.md](README.md).
