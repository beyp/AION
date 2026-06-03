import logging
from pathlib import Path


def setup_logger(log_file: str = "logs/aion.log", level: str = "INFO") -> logging.Logger:
    """Configure and return the main AION logger."""

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("aion")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
