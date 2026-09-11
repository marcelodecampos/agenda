from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agenda"
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "console"
    database_url: str = (
        "postgresql+psycopg://agenda:agenda@localhost:5432/agenda"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()