from copy import deepcopy
from typing import Any


user_states: dict[int, dict[str, Any]] = {}


def get_state(user_id: int) -> dict[str, Any] | None:
    state = user_states.get(user_id)
    return deepcopy(state) if state else None


def set_state(user_id: int, state: dict[str, Any]) -> None:
    user_states[user_id] = deepcopy(state)


def clear_state(user_id: int) -> None:
    user_states.pop(user_id, None)
