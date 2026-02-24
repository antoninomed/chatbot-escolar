from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    WEBHOOK_VERIFY_TOKEN: str

    META_ACCESS_TOKEN: str
    META_PHONE_NUMBER_ID: str
    META_APP_SECRET: str
    META_GRAPH_VERSION: str = "v20.0"

    DATABASE_URL: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()