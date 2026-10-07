from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    app_name: str = "CodeMind" 
    app_version: str = "1.0.0" 
    debug: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    model_config =SettingsConfigDict (
        env_file=".env",
        env_file_encoding="utf-8", 
        case_sensitive=False,
    )
settings=Settings()