from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    redis_url: str

    model_config = SettingsConfigDict(extra="allow")

settings = Settings()
