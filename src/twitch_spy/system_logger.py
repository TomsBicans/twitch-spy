import logging
import os
from config import LOG_DIR


def setup_logger(name, log_file, level=logging.INFO):
    """Function to set up a logger."""
    # Create formatter
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Create and set a handler for writing log messages to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Create and set a handler for writing log messages to the console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Create the logger and set its level
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file_path = os.path.join(LOG_DIR, "application.log")
logger = setup_logger("ApplicationLogger", log_file_path, level=logging.DEBUG)
