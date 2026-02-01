from config import Settings
from models.schemas import ModelProvider


def test_model_provider_accepts_gemini_alias() -> None:
    assert ModelProvider("gemini") is ModelProvider.GOOGLE


def test_settings_accepts_gemini_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = Settings(_env_file=None)

    assert settings.GOOGLE_API_KEY == "test-gemini-key"
