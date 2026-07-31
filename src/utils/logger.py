import logging
import sys
from pathlib import Path
from src.config import settings


def setup_logger(name: str) -> logging.Logger:
    """ロガーをセットアップ"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return logging.getLogger(name)
