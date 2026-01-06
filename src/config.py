from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    RABBITMQ_HOST: str = 'localhost'
    RABBITMQ_USER: str = 'user'
    RABBITMQ_PASS: str

    S3_ENDPOINT: str = 'http://localhost:8333'
    S3_BUCKET: str = 'documents'
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str

    QDRANT_HOST: str = 'localhost'
    QDRANT_PORT: int = 6333

    QUEUE_NAME: str = 'ingest_queue'

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
        env_file_encoding='utf-8',
    )

config = Config()