import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """アプリケーション設定"""

    # API Configuration
    anthropic_api_key: str

    # Paths
    data_dir: Path = Path("./data")
    records_dir: Path = Path("./data/records")
    db_path: Path = Path("./data/db.sqlite")

    # Logging
    log_level: str = "INFO"

    # API / CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"

    def __init__(self, **data):
        super().__init__(**data)
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.records_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
def get_settings() -> Settings:
    """グローバル設定インスタンスを取得"""
    return Settings()


settings = get_settings()
