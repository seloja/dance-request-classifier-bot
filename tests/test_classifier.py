import pytest

from app.classifier import KeywordClassifier


@pytest.mark.parametrize(
    ("text", "expected_label"),
    [
        ("Хочу записать ребёнка", "enrollment"),
        ("Запись", "enrollment"),
        ("Запишите ребёнка", "enrollment"),
        ("Хочу записаться", "enrollment"),
        ("Можно прийти на пробное занятие", "enrollment"),
        ("Во сколько сегодня тренировка", "schedule"),
        ("Когда занятия у младшей группы", "schedule"),
        ("Сколько стоит абонемент", "payment"),
        ("Как оплатить занятия", "payment"),
        ("Когда оплачивать", "payment"),
        ("Когда платить за занятия", "payment"),
        ("Как заплатить за абонемент", "payment"),
        ("Мы сегодня не придём", "absence"),
        ("Ребёнок заболел, занятие пропускаем", "absence"),
        ("Можно связаться с администратором", "admin_other"),
        ("Спасибо", "admin_other"),
        ("", "admin_other"),
    ],
)
def test_keyword_classifier(text, expected_label):
    classifier = KeywordClassifier()
    assert classifier.predict(text)["label"] == expected_label
