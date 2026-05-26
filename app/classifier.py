import os
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import settings


LABELS = ["enrollment", "schedule", "payment", "absence", "admin_other"]
TIE_BREAK_PRIORITY = {
    "absence": 5,
    "payment": 4,
    "enrollment": 3,
    "schedule": 2,
    "admin_other": 1,
}

KEYWORDS = {
    "enrollment": [
        "запис",
        "пробн",
        "первое занят",
        "первый раз",
        "нович",
        "группа для",
        "места",
        "набор",
        "дочке",
        "сыну",
        "ребенку",
        "ребёнку",
        "возраст",
        "хочу к вам",
        "начать заниматься",
    ],
    "schedule": [
        "распис",
        "во сколько",
        "когда",
        "сегодня",
        "завтра",
        "дни",
        "по каким дням",
        "тренировка",
        "занятие будет",
        "график",
        "время",
        "какое занятие",
        "на этой неделе",
    ],
    "payment": [
        "сто",
        "цена",
        "оплат",
        "абонемент",
        "перевод",
        "налич",
        "карта",
        "задолж",
        "долг",
        "возврат",
        "сколько стоит",
        "платеж",
        "платёж",
        "чек",
        "скидк",
    ],
    "absence": [
        "не прид",
        "не сможем",
        "пропуск",
        "пропуст",
        "боле",
        "забол",
        "отработ",
        "перенести занятие",
        "сегодня не будет",
        "нас не будет",
        "не успеваем",
        "приболел",
        "приболела",
    ],
    "admin_other": [
        "админ",
        "администратор",
        "человек",
        "связаться",
        "поговорить",
        "вопрос",
        "тренер",
        "концерт",
        "выступ",
        "форма",
        "одежда",
        "обувь",
        "адрес",
        "зал",
        "где находится",
        "спасибо",
        "здравствуйте",
        "привет",
        "номер",
        "телефон",
    ],
}


class BaseClassifier(ABC):
    @abstractmethod
    def predict(self, text: str) -> dict:
        raise NotImplementedError


class KeywordClassifier(BaseClassifier):
    def __init__(self, confidence_threshold: float | None = None):
        self.confidence_threshold = (
            settings.confidence_threshold if confidence_threshold is None else confidence_threshold
        )

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    def predict(self, text: str) -> dict:
        normalized_text = self.normalize(text)
        if not normalized_text:
            return {"label": "admin_other", "confidence": 0.0}

        scores = {
            label: sum(1 for keyword in keywords if keyword in normalized_text)
            for label, keywords in KEYWORDS.items()
        }
        best_label = max(
            scores,
            key=lambda label: (scores[label], TIE_BREAK_PRIORITY[label]),
        )
        matches = scores[best_label]

        if matches == 0:
            return {"label": "admin_other", "confidence": 0.0}

        confidence = min(1.0, 0.4 + 0.2 * matches)
        if confidence < self.confidence_threshold:
            return {"label": "admin_other", "confidence": confidence}

        return {"label": best_label, "confidence": confidence}


class TransformerClassifier(BaseClassifier):
    def __init__(self, model_dir: str | None = None):
        self.model_dir = model_dir or settings.model_dir
        if not os.path.isdir(self.model_dir):
            raise FileNotFoundError(
                "Transformer model not found. Train it with train_transformer.py "
                "or use CLASSIFIER_TYPE=baseline."
            )

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
        self.model.eval()

    def predict(self, text: str) -> dict:
        normalized_text = KeywordClassifier.normalize(text)
        if not normalized_text:
            return {"label": "admin_other", "confidence": 0.0}

        inputs = self.tokenizer(
            normalized_text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128,
        )
        with self.torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = self.torch.softmax(outputs.logits, dim=-1)[0]
            confidence, predicted_id = self.torch.max(probabilities, dim=0)

        id2label = getattr(self.model.config, "id2label", {})
        label = id2label.get(int(predicted_id), "admin_other")
        return {"label": label, "confidence": float(confidence)}


@lru_cache
def get_classifier() -> BaseClassifier:
    if settings.classifier_type == "transformer":
        try:
            return TransformerClassifier()
        except FileNotFoundError as exc:
            print(exc)
            print("Fallback to KeywordClassifier.")
            return KeywordClassifier()

    return KeywordClassifier()
