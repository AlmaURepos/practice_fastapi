from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    redis_url: str
    rate_limit: int = 10 
    rate_limit_window: int = 60  

    model_config = SettingsConfigDict(extra="allow")
    

settings = Settings()
