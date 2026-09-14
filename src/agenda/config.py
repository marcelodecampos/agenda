from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agenda"
    api_host: str = "0.0.0.0"
    api_port: int = 8081
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "console"
    keycloak_base_url: str = "http://localhost:8080"
    keycloak_realm: str = "agenda"
    public_rate_limit_per_minute: int = 60
    database_url: str = (
        "postgresql+psycopg://agenda:agenda@localhost:5432/agenda"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()