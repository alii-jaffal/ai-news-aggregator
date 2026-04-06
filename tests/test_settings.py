from app.settings import Settings


def test_settings_load_from_env_file(tmp_path, monkeypatch):
    for key in [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "DIGEST_GEMINI_API_KEY",
        "CURATOR_GEMINI_API_KEY",
        "EMAIL_GEMINI_API_KEY",
        "EMAIL",
        "APP_PASSWORD",
        "PROXY_USERNAME",
        "PROXY_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "POSTGRES_USER=postgres",
                "POSTGRES_PASSWORD=secret",
                "POSTGRES_HOST=localhost",
                "POSTGRES_PORT=5432",
                "POSTGRES_DB=ai_news",
                "DIGEST_GEMINI_API_KEY=digest-key",
                "CURATOR_GEMINI_API_KEY=curator-key",
                "EMAIL_GEMINI_API_KEY=email-key",
                "EMAIL=test@example.com",
                "APP_PASSWORD=app-password",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.POSTGRES_USER == "postgres"
    assert settings.POSTGRES_PASSWORD == "secret"
    assert settings.POSTGRES_HOST == "localhost"
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_DB == "ai_news"
    assert settings.EMAIL == "test@example.com"
    assert settings.APP_PASSWORD == "app-password"


def test_settings_optional_proxy_fields_default_to_none(tmp_path, monkeypatch):
    for key in [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "DIGEST_GEMINI_API_KEY",
        "CURATOR_GEMINI_API_KEY",
        "EMAIL_GEMINI_API_KEY",
        "EMAIL",
        "APP_PASSWORD",
        "PROXY_USERNAME",
        "PROXY_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "POSTGRES_USER=postgres",
                "POSTGRES_PASSWORD=secret",
                "POSTGRES_HOST=localhost",
                "POSTGRES_PORT=5432",
                "POSTGRES_DB=ai_news",
                "DIGEST_GEMINI_API_KEY=digest-key",
                "CURATOR_GEMINI_API_KEY=curator-key",
                "EMAIL_GEMINI_API_KEY=email-key",
                "EMAIL=test@example.com",
                "APP_PASSWORD=app-password",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.PROXY_USERNAME is None
    assert settings.PROXY_PASSWORD is None
