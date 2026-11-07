from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FastAPI App"
    debug_mode: bool = False
    database_url: str = "sqlite:///./default.db"
    secret_key: str = "default-secret-key"
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_api_key: str = "ollama"
    local_llm_model: str = "llama3.2"

    # Pydantic V2 configuration to point to the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instantiate settings to be imported across your app
settings = Settings()