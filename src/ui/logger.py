import logging
from pathlib import Path

class Logger:
    def __init__(self, log_file_path: str, log_level=logging.INFO):
        """
        Initialize the Logger class.

        Args:
            log_file_path (str): Path to the log file.
            log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

        # Create a logger
        self.logger = logging.getLogger("RepoAuditLogger")
        self.logger.setLevel(log_level)

        # Create a formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(self.log_file_path, mode="a")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log_to_console(self, message: str, level=logging.INFO):
        """
        Log a message to the console only.

        Args:
            message (str): The message to log.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)
        self.logger.log(level, message)

    def log_to_file(self, message: str, level=logging.INFO):
        """
        Log a message to the file only.

        Args:
            message (str): The message to log.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(level)
        self.logger.log(level, message)

    def log(self, message: str, level=logging.INFO):
        """
        Log a message to both the console and the file.

        Args:
            message (str): The message to log.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        self.logger.log(level, message)