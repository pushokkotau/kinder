from app.services.web_session import WebSessionStateStore


def test_web_session_state_is_grouped_by_session():
    store = WebSessionStateStore()

    state = store.create("session-1")
    store.set_location("session-1", "Amsterdam", "resolved")
    store.bind_phone("+31612345678", "session-1")

    assert state.city == "Amsterdam"
    assert state.location == "resolved"
    assert state.phones == {"+31612345678"}
    assert store.find_by_phone("+31612345678") == "session-1"


def test_binding_phone_to_new_session_moves_the_phone():
    store = WebSessionStateStore()
    store.bind_phone("+31612345678", "session-1")
    store.bind_phone("+31612345678", "session-2")

    assert store.find_by_phone("+31612345678") == "session-2"
    assert "+31612345678" not in store.get("session-1").phones


def test_removing_session_removes_its_phone_mappings():
    store = WebSessionStateStore()
    store.bind_phone("+31612345678", "session-1")
    store.bind_phone("+31687654321", "session-1")

    store.remove("session-1")

    assert store.get("session-1") is None
    assert store.find_by_phone("+31612345678") is None
    assert store.find_by_phone("+31687654321") is None
