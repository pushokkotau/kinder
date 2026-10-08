from types import SimpleNamespace

from app.bot.services import TelegramServiceProvider
from app.services.factory import ServiceFactory


def test_provider_builds_services_for_user(monkeypatch):
    client = object()
    sessions = SimpleNamespace(get_client=lambda user_id: client)
    provider = TelegramServiceProvider(sessions)
    message = SimpleNamespace(from_user=SimpleNamespace(id=42))
    services = object()
    calls = []

    def for_client(value):
        calls.append(value)
        return services

    monkeypatch.setattr(ServiceFactory, "for_client", staticmethod(for_client))

    assert provider.for_message(message) is services
    assert calls == [client]


def test_provider_uses_authenticated_client(monkeypatch):
    client = object()
    sessions = SimpleNamespace(get_authenticated_client=lambda user_id: client)
    provider = TelegramServiceProvider(sessions)
    message = SimpleNamespace(from_user=SimpleNamespace(id=42))
    services = object()
    calls = []

    def for_client(value):
        calls.append(value)
        return services

    monkeypatch.setattr(ServiceFactory, "for_client", staticmethod(for_client))

    assert provider.for_message(message, authenticated=True) is services
    assert calls == [client]
