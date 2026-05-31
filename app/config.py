from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:1b"
    database_url: str = "sqlite+aiosqlite:///./datos/autobot.db"
    whatsapp_provider: str = "mock"


settings = Settings()
