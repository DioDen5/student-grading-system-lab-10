from grade_service.config import Settings, get_settings
from grade_service.logging_config import configure_logging


def test_default_settings():
    settings = Settings(_env_file=None)
    assert settings.app_name == "Grade Service"
    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///data/grading.db"


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///custom.db")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    settings = Settings(_env_file=None)
    assert settings.environment == "production"
    assert settings.database_url == "sqlite:///custom.db"
    assert settings.log_level == "WARNING"


def test_cached_settings_and_logging():
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    configure_logging("INFO")
