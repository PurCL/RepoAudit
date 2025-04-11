import sys
import logging
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
        # Ensure the log directory exists
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create logger instance
        self.logger = logging.getLogger(f"RepoAuditLogger-{log_file_path}")
        self.logger.setLevel(log_level)
        
        # Clear any existing handlers to avoid duplicate output
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        
        # File handler
        file_handler = logging.FileHandler(self.log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler (for print_console method)
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(log_level)
        self.console_handler.setFormatter(formatter)
        # Not adding console handler immediately, it will be added/removed dynamically as needed
    
    def print_log(self, *args: Any) -> None:
        """
        Output messages to log file only.

        Args:
            *args: Message parts to be logged, multiple parameters will be merged into a single string.
        """
        # Ensure console handler is not in logger
        if self.console_handler in self.logger.handlers:
            self.logger.removeHandler(self.console_handler)
        
        # Merge all arguments into a single message string
        message = " ".join(map(str, args))
        self.logger.info(message)
    
    def print_console(self, *args: Any) -> None:
        """
        Output messages to both console and log file.

        Args:
            *args: Message parts to be logged, multiple parameters will be merged into a single string.
        """
        # Ensure console handler is in logger
        if self.console_handler not in self.logger.handlers:
            self.logger.addHandler(self.console_handler)
        
        # Merge all arguments into a single message string
        message = " ".join(map(str, args))
        self.logger.info(message)
        
        # Remove console handler so messages go only to file by default
        self.logger.removeHandler(self.console_handler)