from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    log_level: str = "INFO"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
