from config import get_web_allowed_origins


def test_web_allowed_origins_defaults_to_local_frontend(monkeypatch):
    monkeypatch.delenv("WEB_ALLOWED_ORIGINS", raising=False)

    assert get_web_allowed_origins() == [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]


def test_web_allowed_origins_reads_comma_separated_env(monkeypatch):
    monkeypatch.setenv(
        "WEB_ALLOWED_ORIGINS",
        "https://example.com, https://app.example.com,",
    )

    assert get_web_allowed_origins() == [
        "https://example.com",
        "https://app.example.com",
    ]
