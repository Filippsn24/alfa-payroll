# ALFACRM Payroll

Автоматический расчёт зарплаты тренеров по футболу из [ALFACRM](https://meteor.s20.online).  
Можно запускать локально, через HTTP API или GitHub Actions — и подключать к другим системам (Make, n8n, Zapier, свой бэкенд).

## Возможности

- Загрузка уроков из ALFACRM за любой месяц
- Правила ставок: 100/200/140/230/150, Кукорова (1500/урок), минималка «Меньше 5 детей»
- Фиксированные доп.расходы: лагерь, лидогенерация, кубок Метеора
- Выгрузка в Excel (с формулами `=B*C`) и JSON
- Свод для бухгалтера (Татьяна): тренер → проект → сумма
- REST API для вызова из других сервисов

## Быстрый старт

### 1. Клонировать и настроить

```bash
git clone https://github.com/YOUR_USER/alfa-payroll.git
cd alfa-payroll
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # заполнить ALFACRM_EMAIL и ALFACRM_API_KEY
```

### 2. Расчёт за месяц (CLI)

```bash
python -m payroll --month 2026-05
python -m payroll --month 2026-05 --json --tatyana
python -m payroll --month 2026-05 --extras data/extras.example.json
```

Файлы появятся в папке `output/`:
- `payroll_2026-05.xlsx` — таблица зарплаты
- `payroll_2026-05.json` — данные для интеграций
- `tatyana_2026-05.xlsx` — свод по проектам

### 3. HTTP API (для других ресурсов)

```bash
python -m payroll --api
# или: uvicorn payroll.api:app --host 0.0.0.0 --port 8000
```

В `.env` задайте `PAYROLL_API_KEY` — тогда все запросы требуют заголовок `X-API-Key`.

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/health` | Проверка работы |
| GET | `/payroll?month=2026-05` | JSON или `format=xlsx` |
| GET | `/payroll?month=2026-05&tatyana=true` | JSON + свод Татьяны |
| POST | `/payroll` | Тело: `{"month":"2026-05","extras":[...]}` |
| GET | `/tatyana?month=2026-05` | Только свод для Татьяны |

Пример из PowerShell:

```powershell
$headers = @{ "X-API-Key" = "your-secret" }
Invoke-RestMethod "http://localhost:8000/payroll?month=2026-05&tatyana=true" -Headers $headers
```

Пример из curl:

```bash
curl -H "X-API-Key: your-secret" "http://localhost:8000/payroll?month=2026-05&format=json"
```

### 4. Деплой API в облако

Подойдут [Railway](https://railway.app), [Render](https://render.com), [Fly.io](https://fly.io):

1. Подключите GitHub-репозиторий
2. Команда запуска: `uvicorn payroll.api:app --host 0.0.0.0 --port $PORT`
3. Переменные окружения: `ALFACRM_EMAIL`, `ALFACRM_API_KEY`, `PAYROLL_API_KEY`

После деплоя вызывайте API из Make/n8n/Zapier по URL вида  
`https://your-app.railway.app/payroll?month=2026-05`.

## GitHub Actions

1. Создайте репозиторий и запушьте код
2. В **Settings → Secrets → Actions** добавьте:
   - `ALFACRM_EMAIL`
   - `ALFACRM_API_KEY`
   - (опционально) `ALFACRM_BASE_URL`, `ALFACRM_BRANCH_ID`
3. **Actions → Calculate Payroll → Run workflow** — укажите месяц
4. Скачайте артефакт `payroll-YYYY-MM` с xlsx/json

## Доп.расходы из файла

Формат `data/extras.example.json`:

```json
[
  { "coach": "Ткаченко Евгений Игоревич", "name": "Турнир Десятка", "qty": 1, "rate": 5000 }
]
```

Встроенные доп.расходы (лагерь, кубок) заданы в `payroll/rules.py`.

## Структура проекта

```
alfa-payroll/
├── payroll/           # основной код
│   ├── calculator.py  # расчёт
│   ├── alfcrm.py      # API клиент
│   ├── rules.py       # ставки и фиксы
│   ├── tatyana.py     # свод по проектам
│   ├── export.py      # xlsx/json
│   └── api.py         # FastAPI
├── data/
│   └── group_project_pairs.json
└── .github/workflows/calculate-payroll.yml
```

## Безопасность

**Не коммитьте** `.env` и API-ключи. Используйте GitHub Secrets и переменные окружения на сервере.

## Лицензия

Приватный проект Meteor / футбольная школа.
