"""
Logger Configuration for Risk Compliance System
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str, log_level: str = "INFO", log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup logger with consistent formatting

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """

    # Create logger
    logger = logging.getLogger(name)

    # Don't add handlers if they already exist
    if logger.handlers:
        return logger

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to create file handler for {log_file}: {str(e)}")

    return logger


def get_default_log_file(component: str = "risk_compliance") -> str:
    """
    Get default log file path

    Args:
        component: Component name for log file

    Returns:
        Default log file path
    """

    # Get logs directory
    logs_dir = Path(__file__).parent.parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = logs_dir / f"{component}_{timestamp}.log"

    return str(log_file)
