from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    database_path: str = "elevio_career.db"

    DB_HOST: str
    DB_NAME: str
    DB_PASSWORD: str
    DB_USER: str
    DB_PORT: int = 5432   # 👈 add this
    USE_WORKER: bool = False



settings = Settings()

