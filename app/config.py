import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    api_url: str = os.getenv("API_URL", "http://127.0.0.1:8000/classify")
    classifier_type: str = os.getenv("CLASSIFIER_TYPE", "baseline").lower()
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
    model_name: str = os.getenv("MODEL_NAME", "cointegrated/rubert-tiny2")
    model_dir: str = os.getenv("MODEL_DIR", "models/rubert_tiny2_dance_classifier")
    admin_username: str = os.getenv("ADMIN_USERNAME", "@dance_studio")
    staff_chat_id: str = os.getenv("STAFF_CHAT_ID", "")
    enrollment_chat_id: str = os.getenv("ENROLLMENT_CHAT_ID", "")
    absence_chat_id: str = os.getenv("ABSENCE_CHAT_ID", "")
    database_path: str = os.getenv("DATABASE_PATH", "data/dance_bot.sqlite3")


settings = Settings()
