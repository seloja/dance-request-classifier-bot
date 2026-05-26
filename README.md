# Чат-бот классификации запросов для студии танцев

Проект для ВКР на тему «Разработка чат-бота классификации запросов пользователей на основе Transformer-архитектур».

Система построена по схеме:

```text
Telegram-бот -> FastAPI -> модуль классификации -> шаблонный ответ пользователю
```

На первом этапе работает baseline-классификатор по ключевым словам. Архитектура уже подготовлена для переключения на Transformer-модель `cointegrated/rubert-tiny2`.

## Классы запросов

| Label | Русское название |
| --- | --- |
| `enrollment` | Запись на занятия |
| `schedule` | Расписание |
| `payment` | Оплата |
| `absence` | Пропуск занятия |
| `admin_other` | Связь с администратором |

## Структура проекта

```text
dance_bot/
├── app/
│   ├── api.py
│   ├── classifier.py
│   ├── schemas.py
│   ├── responses.py
│   └── config.py
├── data/
│   ├── dataset.csv
│   ├── train.csv
│   └── test.csv
├── models/
├── tests/
├── bot.py
├── evaluate.py
├── train_transformer.py
├── requirements.txt
├── .env.example
└── README.md
```

CSV-файлы используют формат:

```csv
text,label
Сколько стоит абонемент?,payment
```

## Установка на Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Создайте `.env` на основе `.env.example`:

```powershell
Copy-Item .env.example .env
```

Для Telegram-бота укажите настоящий токен:

```env
BOT_TOKEN=your_telegram_bot_token_here
API_URL=http://127.0.0.1:8000/classify
CLASSIFIER_TYPE=baseline
CONFIDENCE_THRESHOLD=0.5
MODEL_NAME=cointegrated/rubert-tiny2
MODEL_DIR=models/rubert_tiny2_dance_classifier
```

## Запуск FastAPI

```powershell
uvicorn app.api:app --reload
```

Проверка API:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/classify -ContentType "application/json" -Body '{"text":"Сколько стоит абонемент?"}'
```

Ожидаемый класс: `payment`.

## Запуск Telegram-бота

Сначала должен быть запущен FastAPI-сервис. Затем:

```powershell
python bot.py
```

Бот не классифицирует текст сам: он отправляет сообщение в FastAPI по адресу из `API_URL`.

## Оценка качества

```powershell
python evaluate.py
```

Скрипт читает `data/test.csv`, считает accuracy и сохраняет подробный результат в `data/evaluation_results.csv`.

## Тесты

```powershell
pytest
```

Тесты проверяют baseline-классификатор и основные endpoints FastAPI.

## Обучение Transformer-модели

```powershell
python train_transformer.py
```

Скрипт использует:

- модель `cointegrated/rubert-tiny2`;
- файлы `data/train.csv` и `data/test.csv`;
- 5 классов классификации;
- `max_length=128`;
- сохранение модели в `models/rubert_tiny2_dance_classifier/`.

После обучения можно переключить классификатор в `.env`:

```env
CLASSIFIER_TYPE=transformer
```

Если `CLASSIFIER_TYPE=transformer`, но обученной модели нет, приложение выведет понятное предупреждение и автоматически использует baseline-классификатор, чтобы демонстрация проекта не ломалась.

## Режим baseline

Baseline-классификатор ищет ключевые слова, выбирает класс с максимальным количеством совпадений и возвращает условную уверенность:

```text
confidence = min(1.0, 0.4 + 0.2 * number_of_matches)
```

Если совпадений нет или уверенность ниже `CONFIDENCE_THRESHOLD`, запрос относится к `admin_other`.
