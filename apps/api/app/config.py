from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://wyro:wyro@localhost:5432/wyro"
    dev_token: str = "dev-token"


settings = Settings()
