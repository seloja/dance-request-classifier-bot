import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.dialog_state import clear_state, get_state, set_state
from app.scenarios import (
    absence_notification_text,
    absence_start_text,
    admin_other_text,
    admin_username,
    admin_url,
    create_absence_state,
    create_enrollment_state,
    create_schedule_state,
    enrollment_next_message,
    enrollment_notification_text,
    enrollment_start_text,
    payment_text,
    schedule_response_text,
    schedule_start_text,
    service_chat_not_configured_text,
    update_enrollment_data,
)


START_TEXT = (
    "Здравствуйте! Я бот студии брейк-данса. Напишите вопрос, а я помогу с записью, "
    "расписанием, оплатой, пропуском занятия или связью с администратором."
)

HELP_TEXT = (
    "Вы можете написать вопрос свободным текстом, например: «Хочу записать ребёнка», "
    "«Во сколько тренировка?», «Сколько стоит абонемент?», «Мы сегодня не придём».\n\n"
    "Чтобы отменить текущий сценарий, отправьте /cancel."
)

API_UNAVAILABLE_TEXT = (
    "Сервис классификации временно недоступен. Попробуйте позже или свяжитесь с администратором."
)


dp = Dispatcher()


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Написать администратору", url=admin_url())]
        ]
    )


def enrollment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, передать заявку",
                    callback_data="enrollment_submit",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Нет, пока не нужно",
                    callback_data="enrollment_skip",
                )
            ],
            [InlineKeyboardButton(text="Связаться с администратором", url=admin_url())],
        ]
    )


def enrollment_chat_id() -> str:
    return settings.enrollment_chat_id or settings.staff_chat_id


def absence_chat_id() -> str:
    return settings.absence_chat_id or settings.staff_chat_id


async def classify_text(text: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(settings.api_url, json={"text": text})
        response.raise_for_status()
        return response.json()


async def send_to_service_chat(bot: Bot, chat_id: str, text: str) -> bool:
    if not chat_id:
        return False
    await bot.send_message(chat_id=chat_id, text=text)
    return True


async def start_enrollment(message: Message) -> None:
    set_state(message.from_user.id, create_enrollment_state())
    await message.answer(enrollment_start_text())


async def start_absence(message: Message) -> None:
    set_state(message.from_user.id, create_absence_state())
    await message.answer(absence_start_text())


async def start_schedule(message: Message) -> None:
    set_state(message.from_user.id, create_schedule_state())
    await message.answer(schedule_start_text())


async def handle_enrollment_message(message: Message, state: dict) -> None:
    state = update_enrollment_data(state, message.text or "")
    answer, is_ready = enrollment_next_message(state)
    set_state(message.from_user.id, state)
    if is_ready and state["data"].get("group"):
        await message.answer(answer, reply_markup=enrollment_keyboard())
    else:
        await message.answer(answer)


async def handle_absence_message(message: Message, state: dict) -> None:
    text = (message.text or "").strip()
    sent = await send_to_service_chat(
        message.bot,
        absence_chat_id(),
        absence_notification_text(text, message.from_user),
    )
    clear_state(message.from_user.id)
    if not sent:
        await message.answer(service_chat_not_configured_text(), reply_markup=admin_keyboard())
        return
    await message.answer(
        "Спасибо, я передал информацию о пропуске тренеру или администратору.\n\n"
        "Если нужно уточнить возможность отработки занятия, свяжитесь с администратором:\n"
        f"{admin_username()}",
        reply_markup=admin_keyboard(),
    )


async def handle_schedule_message(message: Message, state: dict) -> None:
    answer, _ = schedule_response_text(message.text or "")
    clear_state(message.from_user.id)
    await message.answer(answer, reply_markup=admin_keyboard())


async def handle_state_message(message: Message, state: dict) -> None:
    scenario = state.get("scenario")
    if scenario == "enrollment":
        await handle_enrollment_message(message, state)
    elif scenario == "absence":
        await handle_absence_message(message, state)
    elif scenario == "schedule":
        await handle_schedule_message(message, state)
    else:
        clear_state(message.from_user.id)
        await message.answer("Текущий сценарий сброшен. Можете написать новый вопрос.")


async def route_classified_message(message: Message, result: dict) -> None:
    label = result.get("label", "admin_other")
    confidence = float(result.get("confidence", 0.0))

    if confidence < settings.confidence_threshold:
        await message.answer(admin_other_text(), reply_markup=admin_keyboard())
    elif label == "enrollment":
        await start_enrollment(message)
    elif label == "absence":
        await start_absence(message)
    elif label == "schedule":
        await start_schedule(message)
    elif label == "payment":
        await message.answer(payment_text(), reply_markup=admin_keyboard())
    else:
        await message.answer(admin_other_text(), reply_markup=admin_keyboard())


@dp.message(Command("start"))
async def start_handler(message: Message) -> None:
    clear_state(message.from_user.id)
    await message.answer(START_TEXT)


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@dp.message(Command("cancel"))
async def cancel_handler(message: Message) -> None:
    clear_state(message.from_user.id)
    await message.answer("Текущий сценарий отменён. Можете написать новый вопрос.")


@dp.callback_query(F.data == "enrollment_submit")
async def enrollment_submit_handler(callback: CallbackQuery) -> None:
    state = get_state(callback.from_user.id)
    if not state or state.get("scenario") != "enrollment" or not state.get("data", {}).get("group"):
        await callback.answer("Заявка уже неактуальна. Напишите сообщение заново.", show_alert=True)
        return

    sent = await send_to_service_chat(
        callback.bot,
        enrollment_chat_id(),
        enrollment_notification_text(state["data"], callback.from_user),
    )
    clear_state(callback.from_user.id)
    await callback.answer()

    if not sent:
        await callback.message.answer(service_chat_not_configured_text(), reply_markup=admin_keyboard())
        return

    await callback.message.answer(
        "Заявка передана администратору студии.\n\n"
        "Администратор проверит наличие места в группе и при необходимости свяжется с вами.\n\n"
        "Если остались вопросы, можно написать администратору:\n"
        f"{admin_username()}",
        reply_markup=admin_keyboard(),
    )


@dp.callback_query(F.data == "enrollment_skip")
async def enrollment_skip_handler(callback: CallbackQuery) -> None:
    clear_state(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(
        "Хорошо, заявка не отправлена.\n\n"
        "Если решите записаться позже, напишите мне снова или свяжитесь с администратором:\n"
        f"{admin_username()}",
        reply_markup=admin_keyboard(),
    )


@dp.message(F.text)
async def text_handler(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, напишите вопрос текстом.")
        return

    state = get_state(message.from_user.id)
    if state:
        await handle_state_message(message, state)
        return

    try:
        result = await classify_text(text)
    except httpx.HTTPError:
        logging.exception("Classification API is unavailable")
        await message.answer(API_UNAVAILABLE_TEXT)
        return

    await route_classified_message(message, result)


@dp.message()
async def unknown_handler(message: Message) -> None:
    await message.answer("Пожалуйста, напишите вопрос текстом.")


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Add it to .env before starting the bot.")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=settings.bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
