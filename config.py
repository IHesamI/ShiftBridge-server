from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FastAPI App"
    debug_mode: bool = False
    database_url: str = "sqlite:///./default.db"
    secret_key: str = "default-secret-key"

    # Pydantic V2 configuration to point to the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instantiate settings to be imported across your app
settings = Settings()