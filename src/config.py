"""Caminhos e configuração compartilhada do pipeline ATLAS."""
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DATA_QUALITY_DIR = ROOT_DIR / "data" / "quality_reports"
DOCS_DIR = ROOT_DIR / "docs"

STAGING_DIR = DATA_PROCESSED_DIR / "staging"
DIMENSIONS_DIR = DATA_PROCESSED_DIR / "dimensions"
FACTS_DIR = DATA_PROCESSED_DIR / "facts"

RAW_FILES = {
    2024: DATA_RAW_DIR / "BancoVDE 2024.xlsx",
    2025: DATA_RAW_DIR / "BancoVDE 2025.xlsx",
    2026: DATA_RAW_DIR / "BancoVDE 2026.xlsx",
}

MONTHS_PER_FULL_YEAR = 12

LOG_FILE = DATA_QUALITY_DIR / "etl_run.log"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    DATA_QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    return logger


def ensure_dirs():
    for d in [DATA_PROCESSED_DIR, DATA_QUALITY_DIR, STAGING_DIR, DIMENSIONS_DIR, FACTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
