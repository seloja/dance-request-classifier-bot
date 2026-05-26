import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings


START_TEXT = (
    "Здравствуйте! Я бот студии танцев. Напишите вопрос, а я постараюсь определить "
    "тему обращения: запись, расписание, оплата, пропуск занятия или связь с администратором."
)

HELP_TEXT = (
    "Вы можете написать вопрос свободным текстом, например: «Хочу записать ребёнка», "
    "«Во сколько тренировка?», «Сколько стоит абонемент?», «Мы сегодня не придём»."
)

API_UNAVAILABLE_TEXT = (
    "Сервис классификации временно недоступен. Попробуйте позже или свяжитесь с администратором."
)


dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer(START_TEXT)


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@dp.message(F.text)
async def text_handler(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, напишите вопрос текстом.")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(settings.api_url, json={"text": text})
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError:
        logging.exception("Classification API is unavailable")
        await message.answer(API_UNAVAILABLE_TEXT)
        return

    await message.answer(
        f"Категория: {result['class_name']}\n"
        f"Уверенность: {float(result['confidence']):.2f}\n\n"
        f"{result['answer']}"
    )


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
