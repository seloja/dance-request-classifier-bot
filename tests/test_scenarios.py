from types import SimpleNamespace

from app.scenarios import (
    absence_notification_text,
    create_enrollment_state,
    enrollment_next_message,
    schedule_all_text,
    update_enrollment_data,
)


def test_enrollment_extracts_name_and_age_then_asks_experience():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "Артём, 8 лет")

    assert state["data"]["child_name"] == "Артём"
    assert state["data"]["age"] == 8
    assert state["data"]["experience"] is None

    answer, is_ready = enrollment_next_message(state)
    assert not is_ready
    assert "опыт" in answer.lower()


def test_enrollment_extracts_age_and_experience_then_asks_name():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "8 лет, опыта нет")

    assert state["data"]["child_name"] is None
    assert state["data"]["age"] == 8
    assert state["data"]["experience"] == "опыта нет"

    answer, is_ready = enrollment_next_message(state)
    assert not is_ready
    assert "имя" in answer.lower()


def test_enrollment_full_data_selects_group():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "Артём, 8 лет, опыта нет")

    answer, is_ready = enrollment_next_message(state)

    assert is_ready
    assert state["data"]["group"]["name"] == "Пробное занятие для новичков"
    assert "16:30–17:30" in answer
    assert "тренер" in answer.lower()


def test_enrollment_understands_age_words_and_no_experience():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "Сергей, три года, без опыта")

    assert state["data"]["child_name"] == "Сергей"
    assert state["data"]["age"] == 3
    assert state["data"]["experience"] == "опыта нет"


def test_enrollment_extracts_name_without_commas():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "Алексей 7 лет без опыта")

    assert state["data"]["child_name"] == "Алексей"
    assert state["data"]["age"] == 7
    assert state["data"]["experience"] == "опыта нет"


def test_enrollment_understands_positive_experience_phrases():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "Маша, 12 лет, раньше занималась танцами")

    assert state["data"]["child_name"] == "Маша"
    assert state["data"]["age"] == 12
    assert state["data"]["experience"] == "Маша, 12 лет, раньше занималась танцами"


def test_enrollment_offers_trial_lesson_even_with_more_than_five_years_experience():
    state = create_enrollment_state()
    state = update_enrollment_data(state, "Илья, 9 лет, опыт 6 лет")

    answer, is_ready = enrollment_next_message(state)

    assert is_ready
    assert state["data"]["group"]["name"] == "Пробное занятие для новичков"
    assert "16:30–17:30" in answer
    assert "тренер" in answer.lower()


def test_schedule_all_text_contains_all_training_times():
    answer = schedule_all_text()

    assert "09:00–11:30" in answer
    assert "16:30–17:30" in answer
    assert "18:30–20:00" in answer


def test_absence_notification_contains_user_text_and_identity():
    user = SimpleNamespace(id=123, username="parent", full_name="Parent Name")
    notification = absence_notification_text("Аня, 18:00–18:45, сегодня, заболела", user)

    assert "Пропуск занятия" in notification
    assert "Аня, 18:00–18:45, сегодня, заболела" in notification
    assert "@parent" in notification
    assert "123" in notification
