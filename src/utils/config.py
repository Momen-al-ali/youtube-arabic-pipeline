import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # YouTube
    youtube_api_key: str

    # PostgreSQL
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # Pipeline
    time_window_days: int
    log_level: str

    @property
    def postgres_conn_string(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_config() -> Config:
    missing = []

    required = [
        "YOUTUBE_API_KEY",
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    for key in required:
        if not os.getenv(key):
            missing.append(key)

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return Config(
        youtube_api_key=os.environ["YOUTUBE_API_KEY"],
        postgres_host=os.environ["POSTGRES_HOST"],
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.environ["POSTGRES_DB"],
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
        time_window_days=int(os.getenv("TIME_WINDOW_DAYS", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
