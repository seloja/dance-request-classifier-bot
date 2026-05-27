import json
import re
from pathlib import Path
from typing import Any

from app.config import settings


SCHEDULE_PATH = Path("data/schedule.json")
BREAKDANCE_DIRECTION = "брейк-данс"


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
    match = re.search(r"\b([3-9]|1[0-8])\b\s*(?:лет|года|год)?", text.lower())
    return int(match.group(1)) if match else None


def find_group_by_age(age: int, groups: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    for group in groups or load_schedule():
        if int(group["age_min"]) <= age <= int(group["age_max"]):
            return group
    return None


def find_group_by_name(text: str, groups: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    normalized = text.lower().replace("ё", "е")
    for group in groups or load_schedule():
        name = group["name"].lower().replace("ё", "е")
        short_name = name.replace(" группа", "")
        if name in normalized or short_name in normalized:
            return group
    return None


def find_group(text: str) -> dict[str, Any] | None:
    age = extract_age(text)
    if age is not None:
        return find_group_by_age(age)
    return find_group_by_name(text)


def extract_experience(text: str) -> str | None:
    normalized = text.lower().replace("ё", "е")
    if any(phrase in normalized for phrase in ["опыта нет", "нет опыта", "без опыта", "не заним"]):
        return "опыта нет"
    if any(phrase in normalized for phrase in ["немного", "чуть", "пару раз"]):
        return "немного занимался"
    if any(phrase in normalized for phrase in ["брейк", "танц", "занимал", "ходил", "ходила"]):
        return text.strip()
    return None


def extract_child_name(text: str) -> str | None:
    parts = [part.strip() for part in re.split(r"[,;\n]", text) if part.strip()]
    ignored = ("лет", "год", "опыт", "заним", "брейк", "танц", "нет", "немного")
    for part in parts:
        lower_part = part.lower()
        if any(marker in lower_part for marker in ignored) or extract_age(part) is not None:
            continue
        match = re.search(r"[А-ЯЁ][а-яё-]{1,30}", part)
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


def create_schedule_state() -> dict[str, Any]:
    return {"scenario": "schedule", "step": "waiting_schedule_query", "data": {}}


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
        group = find_group_by_age(int(data["age"]))
        data["group"] = group
        state["step"] = "waiting_enrollment_confirmation"
        if group is None:
            return (
                "Спасибо! Я не смог подобрать группу по указанному возрасту.\n\n"
                f"Свяжитесь с администратором: {admin_username()}",
                True,
            )
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
        f"Спасибо! По возрасту ребёнку подходит группа: {group['name']}.\n\n"
        f"Направление: {BREAKDANCE_DIRECTION}\n"
        f"Расписание: {group['days']}, {group['time']}\n\n"
        "На первое занятие нужно взять:\n"
        "— удобную спортивную одежду;\n"
        "— чистую сменную обувь;\n"
        "— воду;\n"
        "— резинку для волос, если волосы длинные.\n\n"
        "Передать заявку администратору студии?"
    )


def schedule_start_text() -> str:
    return (
        "Чтобы показать расписание, напишите, пожалуйста, возраст ребёнка или название группы.\n\n"
        "Например:\n"
        "«6 лет», «младшая группа», «старшая группа»."
    )


def schedule_response_text(text: str) -> tuple[str, dict[str, Any] | None]:
    group = find_group(text)
    if group is None:
        return (
            "Я не смог точно определить группу по вашему сообщению.\n\n"
            "Пожалуйста, напишите возраст ребёнка числом, например «8 лет», "
            f"или свяжитесь с администратором:\n{admin_username()}",
            None,
        )
    return (
        "Для указанного возраста/группы подходит:\n\n"
        f"Группа: {group['name']}\n"
        f"Направление: {BREAKDANCE_DIRECTION}\n"
        f"Расписание: {group['days']}, {group['time']}\n\n"
        "Если нужно уточнить перенос, отмену занятия или наличие мест, "
        f"напишите администратору:\n{admin_username()}",
        group,
    )


def absence_start_text() -> str:
    return (
        "Я понял, что речь идёт о пропуске занятия.\n\n"
        "Напишите, пожалуйста, одним сообщением:\n"
        "— имя ребёнка;\n"
        "— группу или возраст;\n"
        "— дату пропуска;\n"
        "— причину, если хотите указать.\n\n"
        "Например:\n"
        "Аня, младшая группа, сегодня, заболела."
    )


def payment_text() -> str:
    return (
        "Ваш вопрос связан с оплатой занятий.\n\n"
        "Стоимость зависит от группы, количества занятий в неделю и формата посещения.\n\n"
        "Обычно администратор уточняет:\n"
        "— возраст ребёнка или группу;\n"
        "— интересует пробное занятие, разовое посещение или абонемент;\n"
        "— удобный способ оплаты.\n\n"
        "Для точной информации по стоимости и способам оплаты напишите администратору:\n"
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
        f"Предложенная группа: {group['name']}\n"
        f"Расписание: {group['days']}, {group['time']}\n\n"
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
