import pytest

from custodio.whatsapp.config import WhatsAppSettings, load_config

FULL = {
    "WHATSAPP_VERIFY_TOKEN": "vt-secret-value",
    "WHATSAPP_APP_SECRET": "app-secret-value",
    "WHATSAPP_ACCESS_TOKEN": "access-secret-value",
    "WHATSAPP_PHONE_NUMBER_ID": "106540352242922",
    "WHATSAPP_DISPLAY_NUMBER": "+573001112233",
}


def _settings(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> WhatsAppSettings:
    for name in FULL:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return WhatsAppSettings()


def test_without_variables_the_channel_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    assert load_config(_settings(monkeypatch, {})) is None


def test_a_missing_secret_keeps_the_channel_off(monkeypatch: pytest.MonkeyPatch) -> None:
    partial = {k: v for k, v in FULL.items() if k != "WHATSAPP_APP_SECRET"}

    assert load_config(_settings(monkeypatch, partial)) is None


def test_with_every_variable_the_channel_is_on_with_a_current_graph_version(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config(_settings(monkeypatch, FULL))

    assert config is not None
    assert config.display_number == "573001112233"
    assert config.graph_version == "v23.0"


def test_secrets_never_show_in_a_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, FULL)
    config = load_config(settings)

    for printed in (repr(settings), repr(config)):
        assert "secret-value" not in printed
