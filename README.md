# Чат-бот классификации запросов для студии танцев

Проект для ВКР на тему «Разработка чат-бота классификации запросов пользователей на основе Transformer-архитектур».

Система построена по схеме:

```text
Telegram-бот -> FastAPI -> модуль классификации -> сценарий обработки -> SQLite -> ответ пользователю
```

В проекте есть baseline-классификатор по ключевым словам и Transformer-классификатор на основе `cointegrated/rubert-tiny2`. Классификатор определяет тему первого сообщения, после чего Telegram-бот запускает сценарий обработки.

## Возможности

- классификация свободных сообщений пользователей по пяти классам;
- переключение между baseline и Transformer через `.env`;
- сценарии записи, расписания, оплаты, пропуска занятия и связи с администратором;
- отправка заявок и уведомлений о пропусках в служебный Telegram-чат;
- сохранение пользователей, сообщений, классификаций, заявок и пропусков в SQLite;
- скрипты для оценки качества и обучения Transformer-модели;
- автоматические тесты для классификатора, API и сценариев.

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
│   ├── config.py
│   ├── database.py
│   ├── dialog_state.py
│   ├── responses.py
│   ├── scenarios.py
│   ├── schemas.py
│   └── __init__.py
├── data/
│   ├── dataset.csv
│   ├── schedule.json
│   ├── train.csv
│   ├── test.csv
│   └── transformer_metrics.json
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

Если PowerShell запрещает активацию окружения, выполните:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
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
ADMIN_USERNAME=@dance_studio
STAFF_CHAT_ID=
ENROLLMENT_CHAT_ID=
ABSENCE_CHAT_ID=
DATABASE_PATH=data/dance_bot.sqlite3
```

`ADMIN_USERNAME` используется для ссылки на администратора. `STAFF_CHAT_ID` — общий служебный чат администратора или тренера. Если `ENROLLMENT_CHAT_ID` или `ABSENCE_CHAT_ID` не заданы, бот использует `STAFF_CHAT_ID`. `DATABASE_PATH` задаёт путь к локальной SQLite-базе.

## Запуск FastAPI

```powershell
uvicorn app.api:app --reload
```

Если порт `8000` занят или Windows выдаёт ошибку доступа к сокету, используйте порт `8001`:

```powershell
python -m uvicorn app.api:app --reload --port 8001
```

В этом случае в `.env` нужно указать:

```env
API_URL=http://127.0.0.1:8001/classify
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

## Полный запуск с нуля

Откройте PowerShell и перейдите в папку проекта:

```powershell
cd "C:\Users\seloj\Desktop\диплом\dance_bot"
```

Создайте и активируйте виртуальное окружение:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Установите зависимости:

```powershell
pip install -r requirements.txt
```

Создайте `.env`, если его ещё нет:

```powershell
Copy-Item .env.example .env
```

Откройте `.env` и заполните настройки:

```env
BOT_TOKEN=your_telegram_bot_token_here
API_URL=http://127.0.0.1:8001/classify
CLASSIFIER_TYPE=baseline
CONFIDENCE_THRESHOLD=0.5
MODEL_NAME=cointegrated/rubert-tiny2
MODEL_DIR=models/rubert_tiny2_dance_classifier
ADMIN_USERNAME=@dance_studio
STAFF_CHAT_ID=
ENROLLMENT_CHAT_ID=
ABSENCE_CHAT_ID=
DATABASE_PATH=data/dance_bot.sqlite3
```

Для запуска нужны два окна PowerShell.

Окно 1 — FastAPI:

```powershell
cd "C:\Users\seloj\Desktop\диплом\dance_bot"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.api:app --reload --port 8001
```

Проверка API в браузере:

```text
http://127.0.0.1:8001/docs
```

Окно 2 — Telegram-бот:

```powershell
cd "C:\Users\seloj\Desktop\диплом\dance_bot"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python bot.py
```

После этого откройте Telegram-бота и отправьте:

```text
/start
```

Затем можно проверить сценарии:

```text
Хочу записать ребёнка
```

```text
Мы сегодня не придём
```

```text
Когда тренировка у младшей группы?
```

```text
Сколько стоит абонемент?
```

Чтобы остановить API или бота в терминале, нажмите:

```text
Ctrl + C
```

## Сценарии бота

После классификации первого сообщения бот запускает один из сценариев:

- `enrollment` — собирает имя ребёнка, возраст и опыт занятий, предлагает пробное занятие для новичков в 16:30–17:30 и отправку заявки администратору.
- `absence` — просит данные о пропуске и отправляет уведомление тренеру или администратору.
- `schedule` — сразу показывает расписание всех занятий по брейк-дансу.
- `payment` — даёт справочную информацию по оплате и кнопку связи с администратором.
- `admin_other` — предлагает описать вопрос администратору.

Если пользователь находится внутри сценария, следующее сообщение не отправляется в классификатор, а обрабатывается как ответ на текущий шаг. Для отмены сценария:

```powershell
/cancel
```

Расписание занятий хранится в `data/schedule.json`. В первой версии направление одно — брейк-данс, поэтому бот не спрашивает направление. После пробного занятия тренер определяет, в какое постоянное время ребёнку лучше ходить дальше.

## Служебный чат

Для отправки заявок и пропусков добавьте бота в служебный чат администратора или тренера. Затем получите `chat_id` и укажите его в `.env`:

```env
STAFF_CHAT_ID=-1001234567890
```

Простой способ узнать `chat_id`:

1. Добавьте бота в нужный чат.
2. Напишите любое сообщение в чат.
3. Откройте в браузере:

```text
https://api.telegram.org/bot<ВАШ_BOT_TOKEN>/getUpdates
```

4. Найдите поле `chat.id`.

Для раздельных чатов можно указать:

```env
ENROLLMENT_CHAT_ID=-1001111111111
ABSENCE_CHAT_ID=-1002222222222
```

Если служебный чат не настроен, бот не падает, а предлагает пользователю связаться с администратором.

## Хранение данных

Для фиксации обращений используется SQLite-база по пути из `DATABASE_PATH`. При запуске бота таблицы создаются автоматически.

В базе сохраняются:

- пользователи Telegram и отметка о согласии на обработку минимальных данных;
- входящие сообщения;
- результаты классификации: метка класса, уверенность и тип классификатора;
- заявки на пробное занятие;
- сообщения о пропуске занятия.

Файл базы данных не добавляется в git, потому что может содержать персональные данные.

## Оценка качества

```powershell
python evaluate.py
```

Скрипт читает `data/test.csv`, считает accuracy и сохраняет подробный результат в `data/evaluation_results.csv`.

Можно явно выбрать классификатор:

```powershell
python evaluate.py --classifier baseline
python evaluate.py --classifier transformer
```

Transformer-режим считается готовым для демонстрации, если accuracy на `data/test.csv` не ниже baseline-ориентира `0.85`.

## Тесты

```powershell
pytest
```

Тесты проверяют baseline-классификатор, основные endpoints FastAPI и сценарную логику Telegram-бота.

## Обучение Transformer-модели

```powershell
python train_transformer.py
```

Скрипт использует:

- модель `cointegrated/rubert-tiny2`;
- файлы `data/train.csv` и `data/test.csv`;
- 5 классов классификации;
- `max_length=128`;
- фиксированный `seed=42`;
- сохранение модели в `models/rubert_tiny2_dance_classifier/`;
- сохранение метрик в `data/transformer_metrics.json`;
- сохранение предсказаний в `data/transformer_predictions.csv`.

После обучения можно переключить классификатор в `.env`:

```env
CLASSIFIER_TYPE=transformer
```

Текущий локальный результат после обучения `cointegrated/rubert-tiny2`:

```text
baseline accuracy: 0.8500
transformer accuracy: 0.9200
```

Если `CLASSIFIER_TYPE=transformer`, но обученной модели нет, приложение выдаст понятную ошибку. Для стабильной демонстрации верните режим:

```env
CLASSIFIER_TYPE=baseline
```

Так переключение между baseline и Transformer остаётся явным и контролируемым.

## Режим baseline

Baseline-классификатор ищет ключевые слова, выбирает класс с максимальным количеством совпадений и возвращает условную уверенность:

```text
confidence = min(1.0, 0.4 + 0.2 * number_of_matches)
```

Если совпадений нет или уверенность ниже `CONFIDENCE_THRESHOLD`, запрос относится к `admin_other`.
