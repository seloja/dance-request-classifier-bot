import json
import re
from pathlib import Path
from typing import Any

from app.config import settings


SCHEDULE_PATH = Path("data/schedule.json")
BREAKDANCE_DIRECTION = "брейк-данс"
TRIAL_LESSON_SLOT = {
    "name": "Пробное занятие для новичков",
    "days": "",
    "time": "16:30–17:30",
    "description": "пробное занятие для новичков; после него тренер подскажет подходящее постоянное время",
}

AGE_WORDS = {
    "один": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
}


def admin_username() -> str:
    username = settings.admin_username.strip()
    return username or "@dance_studio"


def admin_url() -> str:
    return f"https://t.me/{admin_username().lstrip('@')}"


def load_schedule(path: Path = SCHEDULE_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("groups", [])


def extract_age(text: str) -> int | None:
    normalized = text.lower().replace("ё", "е")
    match = re.search(r"(?<!\d)([1-9]\d?)(?!\d)\s*(?:лет|года|год)?", normalized)
    if match:
        return int(match.group(1))

    for word, age in AGE_WORDS.items():
        if re.search(rf"\b{word}\b\s*(?:лет|года|год)?", normalized):
            return age
    return None


def extract_experience_years(text: str) -> int | None:
    normalized = text.lower().replace("ё", "е")
    match = re.search(
        r"(?:опыт|занимал\w*|ходил\w*|трениров\w*)\D{0,20}"
        r"(?:больше|более|от|около|примерно)?\s*(\d{1,2})\s*(?:\+)?\s*(?:лет|года|год)",
        normalized,
    )
    if match:
        return int(match.group(1))

    match = re.search(r"(\d{1,2})\s*\+\s*(?:лет|года|год)?\s*(?:опыт|заним|трениров)?", normalized)
    if match:
        return int(match.group(1))

    if re.search(r"(?:больше|более)\s+пяти\s+лет", normalized):
        return 6
    return None


def trial_lesson_slot() -> dict[str, Any]:
    return TRIAL_LESSON_SLOT.copy()


def format_group_schedule(group: dict[str, Any]) -> str:
    days = str(group.get("days", "")).strip()
    time = str(group.get("time", "")).strip()
    if days and time:
        return f"{days}, {time}"
    return time or days


def group_public_description(group: dict[str, Any]) -> str:
    description = str(group.get("description", "")).strip()
    schedule = format_group_schedule(group)
    if description:
        return f"{schedule} — {description}"
    return schedule


def extract_experience(text: str) -> str | None:
    normalized = text.lower().replace("ё", "е")
    if any(
        phrase in normalized
        for phrase in [
            "опыта нет",
            "нет опыта",
            "без опыта",
            "опыт отсутствует",
            "не заним",
            "не ходил",
            "не ходила",
            "первый раз",
            "с нуля",
        ]
    ):
        return "опыта нет"
    if any(
        phrase in normalized
        for phrase in ["немного", "чуть", "пару раз", "мало", "начальный", "начинающий"]
    ):
        return "немного занимался"

    positive_markers = [
        "есть опыт",
        "опыт есть",
        "с опытом",
        "имеется опыт",
        "раньше заним",
        "ранее заним",
        "уже заним",
        "занимал",
        "ходил",
        "ходила",
        "трениров",
        "брейк",
        "танц",
        "хореограф",
        "гимнаст",
    ]
    if any(phrase in normalized for phrase in positive_markers):
        return text.strip()
    if extract_experience_years(text) is not None:
        return text.strip()
    return None


def extract_child_name(text: str) -> str | None:
    parts = [part.strip() for part in re.split(r"[,;\n]", text) if part.strip()]
    ignored = ("лет", "год", "опыт", "заним", "брейк", "танц", "нет", "немного")
    for part in parts:
        lower_part = part.lower()
        if any(marker in lower_part for marker in ignored) and len(parts) > 1:
            continue
        if extract_age(part) is not None and len(parts) > 1:
            continue
        match = re.search(r"[А-ЯЁ][а-яё-]{1,30}", part)
        if match:
            return match.group(0)

    cleaned = re.sub(r"(?<!\d)[1-9]\d?(?!\d)\s*(?:лет|года|год)?", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:опыта\s+нет|нет\s+опыта|без\s+опыта|есть\s+опыт|опыт\s+есть)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:немного|чуть|пару\s+раз|раньше|ранее|уже|занимал\w*|ходил\w*|ходила|танц\w*|брейк\w*)\b", " ", cleaned, flags=re.IGNORECASE)
    match = re.search(r"[А-ЯЁ][а-яё-]{1,30}", cleaned)
    if match:
        return match.group(0)

    match = re.fullmatch(r"\s*([А-ЯЁ][а-яё-]{1,30})\s*", text)
    return match.group(1) if match else None


def create_enrollment_state() -> dict[str, Any]:
    return {
        "scenario": "enrollment",
        "step": "waiting_enrollment_data",
        "data": {
            "child_name": None,
            "age": None,
            "experience": None,
            "group": None,
        },
    }


def create_absence_state() -> dict[str, Any]:
    return {"scenario": "absence", "step": "waiting_absence_details", "data": {}}


def update_enrollment_data(state: dict[str, Any], text: str) -> dict[str, Any]:
    data = state.setdefault("data", {})
    child_name = extract_child_name(text)
    age = extract_age(text)
    experience = extract_experience(text)

    if child_name:
        data["child_name"] = child_name
    if age is not None:
        data["age"] = age
    if experience:
        data["experience"] = experience
    return state


def enrollment_start_text() -> str:
    return (
        "Отлично, помогу оформить заявку на пробное занятие по брейк-дансу.\n\n"
        "Напишите, пожалуйста, одним сообщением:\n"
        "— имя ребёнка(обязательно с большой буквы);\n"
        "— возраст;\n"
        "— был ли опыт занятий танцами или брейк-дансом.\n\n"
        "Например:\n"
        "Артём, 8 лет, опыта нет."
    )


def enrollment_next_message(state: dict[str, Any]) -> tuple[str, bool]:
    data = state["data"]
    missing = [
        key
        for key in ["child_name", "age", "experience"]
        if data.get(key) in (None, "")
    ]

    if not missing:
        data["group"] = trial_lesson_slot()
        state["step"] = "waiting_enrollment_confirmation"
        return (enrollment_summary_text(data), True)

    if missing == ["experience"]:
        return (
            "Спасибо! Уточните, пожалуйста, был ли у ребёнка опыт занятий танцами "
            "или брейк-дансом?\n\n"
            "Можно ответить:\n"
            "— опыта нет;\n"
            "— немного занимался;\n"
            "— уже занимался брейком.",
            False,
        )
    if missing == ["child_name"]:
        return "Спасибо! Уточните, пожалуйста, имя ребёнка.", False
    if missing == ["age"]:
        return "Спасибо! Уточните, пожалуйста, возраст ребёнка.", False
    if set(missing) == {"age", "experience"}:
        return (
            "Спасибо! Уточните, пожалуйста, возраст ребёнка и был ли опыт занятий.\n\n"
            "Например:\n"
            "6 лет, опыта нет.",
            False,
        )
    if set(missing) == {"child_name", "experience"}:
        return (
            "Спасибо! Уточните, пожалуйста, имя ребёнка и был ли опыт занятий.",
            False,
        )
    if set(missing) == {"child_name", "age"}:
        return (
            "Спасибо! Уточните, пожалуйста, имя и возраст ребёнка.",
            False,
        )

    return (
        "Спасибо! Уточните, пожалуйста, имя ребёнка, возраст и был ли опыт занятий.",
        False,
    )


def enrollment_summary_text(data: dict[str, Any]) -> str:
    group = data["group"]
    return (
        "Спасибо! Для первого занятия предлагаю пробную группу для новичков.\n\n"
        f"Направление: {BREAKDANCE_DIRECTION}\n"
        f"Время пробного занятия: {format_group_schedule(group)}\n\n"
        "На первом занятии тренер посмотрит уровень ребёнка и подскажет, "
        "в какое постоянное время лучше ходить дальше.\n\n"
        "На первое занятие нужно взять:\n"
        "— удобную спортивную одежду;\n"
        "— чистую сменную обувь;\n"
        "— воду;\n"
        "— резинку для волос, если волосы длинные.\n\n"
        f"Если это время не подходит, можно связаться с администратором: {admin_username()}\n\n"
        "Передать заявку администратору студии?"
    )


def schedule_all_text() -> str:
    groups = load_schedule()
    lines = [
        "Расписание занятий по брейк-дансу:",
        "",
    ]
    for group in groups:
        lines.append(f"— {group_public_description(group)}")

    lines.extend(
        [
            "",
            "Если хотите подобрать подходящее время для ребёнка, напишите возраст и опыт занятий.",
            f"Для уточнения наличия мест можно написать администратору: {admin_username()}",
        ]
    )
    return "\n".join(lines)


def absence_start_text() -> str:
    return (
        "Я понял, что речь идёт о пропуске занятия.\n\n"
        "Напишите, пожалуйста, одним сообщением:\n"
        "— имя ребёнка;\n"
        "— время занятия;\n"
        "— дату пропуска;\n"
        "— причину, если хотите указать.\n\n"
        "Например:\n"
        "Аня, 18:00–18:45, сегодня, заболела."
    )


def payment_text() -> str:
    return (
        "Ваш вопрос связан с оплатой занятий.\n\n"
        "Актуальная стоимость:\n"
        "— абонемент на месяц — 6000 рублей;\n"
        "— разовое занятие — 500 рублей.\n\n"
        "Если нужно уточнить способ оплаты, срок действия абонемента или наличие задолженности, "
        "напишите администратору:\n"
        f"{admin_username()}"
    )


def admin_other_text() -> str:
    return (
        "Ваш вопрос лучше уточнить у администратора студии.\n\n"
        "Пожалуйста, напишите одним сообщением все детали вопроса, чтобы администратор "
        "смог быстрее ответить.\n\n"
        f"Связаться с администратором:\n{admin_username()}"
    )


def service_chat_not_configured_text() -> str:
    return (
        "Служебный чат пока не настроен. "
        f"Свяжитесь с администратором: {admin_username()}"
    )


def user_identity(user: Any) -> str:
    username = f"@{user.username}" if getattr(user, "username", None) else "не указан"
    full_name = getattr(user, "full_name", None) or "не указано"
    user_id = getattr(user, "id", "")
    return (
        f"Пользователь Telegram: {username}\n"
        f"Имя пользователя в Telegram: {full_name}\n"
        f"ID пользователя: {user_id}"
    )


def enrollment_notification_text(data: dict[str, Any], user: Any) -> str:
    group = data["group"]
    return (
        "📝 Новая заявка на запись\n\n"
        f"Направление: {BREAKDANCE_DIRECTION}\n"
        f"Имя ребёнка: {data['child_name']}\n"
        f"Возраст: {data['age']}\n"
        f"Опыт: {data['experience']}\n\n"
        f"Предложенное время пробного занятия: {format_group_schedule(group)}\n"
        "Комментарий: после пробного занятия тренер определит подходящее постоянное время\n\n"
        f"{user_identity(user)}\n\n"
        "Заявка отправлена через чат-бота."
    )


def absence_notification_text(absence_text: str, user: Any) -> str:
    return (
        "📌 Пропуск занятия\n\n"
        "Данные от пользователя:\n"
        f"{absence_text}\n\n"
        f"{user_identity(user)}\n\n"
        "Сообщение отправлено через чат-бота."
    )
