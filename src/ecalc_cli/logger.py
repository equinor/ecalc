import enum
import logging
from dataclasses import dataclass
from datetime import date
from logging.config import dictConfig
from pathlib import Path
from typing import Any


class LogLevel(str, enum.Enum):
    """Valid log levels for CLI logger."""

    ERROR = "ERROR"
    """ Exception causing the CLI operation to fail. Can not continue"""

    WARNING = "WARNING"
    """ User should be warned, but the operation will continue. Use with caution"""

    INFO = "INFO"
    """ Used to inform user of progress of operation.  """

    DEBUG = "DEBUG"
    """ For debugging purposes. In most cases not seen by the user"""


@dataclass
class CLILogConfigurator:
    """Configure logging for CLIeCalc."""

    __log_path: Path | None = None
    __log_level: LogLevel = LogLevel.WARNING

    def __init__(self, log_level: LogLevel = LogLevel.WARNING, log_path: Path = None):
        self.__log_level = log_level
        self.__log_path = log_path

        self.__configure_logger()

    def set_loglevel(self, log_level: LogLevel):
        """Args:
            log_level: Desired log level for logger.

        Returns:

        """
        self.__log_level = log_level
        self.__configure_logger()

    def set_log_path(self, log_path: Path):
        """Args:
            log_path: Path to desired log file location.

        Returns:

        """
        self.__log_path = log_path
        self.__configure_logger()

    def __configure_logger(self):
        log_config: dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": True,  # ie keep root logger ++
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "level": str(self.__log_level.value),
                }
            },
            "loggers": {
                "cliecalc": {"handlers": ["default"], "level": str(self.__log_level.value), "propagate": False},
                "libecalc": {"handlers": ["default"], "level": str(self.__log_level.value), "propagate": False},
                "": {
                    "handlers": ["default"],
                    "level": str(self.__log_level.value),
                },  # root logger, catch all, for e.g. 3rd party libs etc}
            },
        }

        if self.__log_path:
            log_config["handlers"]["rotating_file_handler"] = {
                "formatter": "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": self.__log_path / f"{date.today()}_debug.log",
                "maxBytes": 10000000,  # 10 MB
                "backupCount": 1,
                "level": str(LogLevel.WARNING.value),
            }
            log_config["loggers"]["cliecalc"]["handlers"].append("rotating_file_handler")
            log_config["loggers"]["libecalc"]["handlers"].append("rotating_file_handler")
            log_config["loggers"][""]["handlers"].append("rotating_file_handler")

        dictConfig(log_config)


logger = logging.getLogger("cliecalc")
