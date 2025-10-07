# App configuration (secret key, storage path, max upload size, etc.).
import os
from pathlib import Path

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    STORAGE_ROOT = os.getenv("STORAGE_ROOT", str(Path(__file__).parent / "storage"))
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

class TestConfig(Config):
    STORAGE_ROOT = os.getenv("TEST_STORAGE_ROOT", "/tmp/uia_lens_test")
    LOG_LEVEL = "WARNING"
