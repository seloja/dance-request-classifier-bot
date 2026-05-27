from types import SimpleNamespace

from app.scenarios import (
    absence_notification_text,
    create_enrollment_state,
    enrollment_next_message,
    find_group,
    schedule_response_text,
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
    assert state["data"]["group"]["name"] == "Детская группа"
    assert "Детская группа" in answer


def test_schedule_by_age_returns_group():
    group = find_group("8 лет")
    answer, response_group = schedule_response_text("8 лет")

    assert group["name"] == "Детская группа"
    assert response_group["name"] == "Детская группа"
    assert "18:30" in answer


def test_schedule_by_group_name_returns_group():
    answer, group = schedule_response_text("младшая группа")

    assert group["name"] == "Младшая группа"
    assert "18:00" in answer


def test_absence_notification_contains_user_text_and_identity():
    user = SimpleNamespace(id=123, username="parent", full_name="Parent Name")
    notification = absence_notification_text("Аня, младшая группа, сегодня, заболела", user)

    assert "Пропуск занятия" in notification
    assert "Аня, младшая группа, сегодня, заболела" in notification
    assert "@parent" in notification
    assert "123" in notification
