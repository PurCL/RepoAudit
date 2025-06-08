import sys
import logging
import threading
from pathlib import Path
from typing import Any


class Logger:
    def __init__(self, log_file_path: str, log_level=logging.INFO):
        """
        Initialize the Logger class.

        Args:
            log_file_path (str): Path to the log file.
            log_level (int, optional): Logging level, defaults to logging.INFO.
        """
        # Initialize thread lock for thread-safe log operations
        self._log_lock = threading.Lock()
        self.log_file_path = Path(log_file_path)
        # Ensure the parent directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a logger instance with a unique name based on the log file path
        self.logger = logging.getLogger(f"RepoAuditLogger-{log_file_path}")
        self.logger.setLevel(log_level)
        # Clear any existing handlers to avoid duplicate output
        self.logger.handlers.clear()

        # Create a formatter for log messages
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Create and add a file handler
        file_handler = logging.FileHandler(
            self.log_file_path, mode="a", encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Prepare a console handler for dynamic use in print_console method
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(log_level)
        self.console_handler.setFormatter(formatter)

    def print_log(self, *args: Any) -> None:
        """
        Output messages to log file only.

        Args:
            *args: Message parts to be logged, which are merged into a single string.
        """
        with self._log_lock:
            # Remove the console handler if it exists, so the message is logged only to file
            if self.console_handler in self.logger.handlers:
                self.logger.removeHandler(self.console_handler)
            message = " ".join(map(str, args))
            self.logger.info(message)

    def print_console(self, *args: Any) -> None:
        """
        Output messages to both console and log file.

        Args:
            *args: Message parts to be logged, which are merged into a single string.
        """
        with self._log_lock:
            # Add the console handler if it's not already added
            if self.console_handler not in self.logger.handlers:
                self.logger.addHandler(self.console_handler)
            message = " ".join(map(str, args))
            self.logger.info(message)
            # Remove the console handler after logging so that default logging goes only to file
            self.logger.removeHandler(self.console_handler)
