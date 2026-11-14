import pytest
import sentry_sdk

from app.monitoring import init_sentry

DSN = "https://public@o0.ingest.sentry.io/0"


@pytest.fixture
def init_calls(monkeypatch):
    """Reemplaza `sentry_sdk.init` para revisar con qué se llama sin activar Sentry."""
    calls = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    for name in ("SENTRY_DSN", "SENTRY_ENVIRONMENT", "SENTRY_RELEASE"):
        monkeypatch.delenv(name, raising=False)
    return calls


def test_without_dsn_sentry_stays_off(init_calls):
    assert init_sentry() is False
    assert init_calls == []


def test_empty_dsn_sentry_stays_off(init_calls, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "")

    assert init_sentry() is False
    assert init_calls == []


def test_with_dsn_uses_defaults(init_calls, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", DSN)

    assert init_sentry() is True
    assert init_calls == [
        {
            "dsn": DSN,
            "environment": "development",
            "release": None,
            "traces_sample_rate": 1.0,
        }
    ]


def test_with_dsn_reads_environment_and_release(init_calls, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", DSN)
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "production")
    monkeypatch.setenv("SENTRY_RELEASE", "18af3cf")

    assert init_sentry() is True
    assert init_calls[0]["environment"] == "production"
    assert init_calls[0]["release"] == "18af3cf"
