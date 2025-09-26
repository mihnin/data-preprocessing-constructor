import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """
    Set up the application's logging configuration.
    """
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure rotating file handler (10 files, 10MB each)
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10
    )
    file_handler.setFormatter(log_format)

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    return logging.getLogger(__name__)