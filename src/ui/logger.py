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
        self.logger = logging.getLogger(f"RepoAuditLogger-{log_file_path}")
        self.logger.setLevel(log_level)

        # Avoid duplicate handlers if the logger is reused
        if not self.logger.handlers:
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

    def print_log(self, *args, level=logging.INFO):
        """
        Log a message to the log file only.

        Args:
            *args: The message parts to log.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        message = " ".join(map(str, args))  # Combine all arguments into a single string

        # Temporarily disable the console handler
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.CRITICAL + 1)  # Temporarily disable console output

        self.logger.log(level, message)

        # Re-enable the console handler
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)

    def print_console(self, *args, level=logging.INFO):
        """
        Log a message to both the console and the log file.

        Args:
            *args: The message parts to log.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        message = " ".join(map(str, args))  # Combine all arguments into a single string
        self.logger.log(level, message)