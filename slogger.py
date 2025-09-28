"""This is a logger that supports:

    1. indentation by depth
    2. color coding
    3. custom time zones

Sebastian Sardina @ 2025 - ssardina@gmail.com

Python logging doc: https://docs.python.org/3/library/logging.html#

Good video and code on Python logging:
    https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging


Some information on Python logging and this logger:

- Since it is a simple applicaiton, we only attach handlers to the root logger; all other applicatoin loggers have no handlers and they propagate to the root logger.
- The level of the app logger ("pyNBL") controls what gets created at all and propagated up.
- The level of a logger affects the creation of a record at that level, not whether it is passed to handlers or propagated.
- So, once created, if propagated, the level of the root doesn't matter (it was created already!), only the level of the hanlders matters.
    - So, if app loggers is at DEBUG and root is at INFO, the message will be propgated up and printed by the hanlder of the root logger if the handler is at DEBUG or lower. Root level is ignored.
    # Messages are passed directly to the ancestor loggers’ handlers - neither the level nor filters of the ancestor loggers in question are considered.
    # https://docs.python.org/3/library/logging.html#logging.Logger.propagate
- We implemente identation by adding indent data to the record in the logger, and then using it in the formatter via the string with %(indent)s.
- The timezone is set in the formatter and used to format the time in the log record.

We can create a logger with empty handlers, propagation, and a console hanlder in root:

    import logging
    from slogger import setup_logging
    logger = setup_logging("pyNBL", rotating_file="pynbl.log", indent=2)
    logger.setLevel(logging.INFO)  # set the level of the application logger
    logging.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs

we can then create within the app a sub-logger:

    logger_season = logging.getLogger("pyNBL.season")

IMPORTANT: setup_logging() must be called only once in the application, otherwise multiple console handlers will be attached to the root logger and messages will be duplicated.

- Since we are working with the root logger, if we set it to DEBUG, all debug messages of 3rd party libraries will be printed. To avoid this, we can set the level of the root logger to INFO or WARNING,
    - logging.root.setLevel(logging.INFO)  # set the level of the root logger
    - remember that propagated messages are filtered by the level of the handlers, not the level of the root logger, so if we emit in teh app level at DEBUG level it will stil be printed if the handler console we attached to root is at DEBUG level.
"""

from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter
from zoneinfo import ZoneInfo
from typing import override

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


# FORMATTING with identation!
#   https://docs.python.org/3/library/logging.html#logrecord-attributes
DEFAULT_LOG_FMT = "  %(log_color)s%(asctime)s [%(name)s] %(levelname)-4s%(reset)s | %(indent)s%(log_color)s%(message)s%(reset)s"
LOG_FMT_SIMPLE = (
    "%(log_color)s[%(name)s] %(levelname)-4s%(reset)s | %(indent)s%(message)s%(reset)s"
)
LOG_FMT_SUPER_SIMPLE = (
    "%(log_color)s %(levelname)-4s%(reset)s | %(indent)s%(message)s%(reset)s"
)
LOG_DATE = "%Y-%m-%dT%H:%M:%S%z"
DEFAULT_LOG_COLORS = {
    "DEBUG": "cyan",
    "DEBG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "WARN": "yellow",
    "ERROR": "red",
    "ERR": "red",
    "CRIT": "bold_red",
}
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
DEFAULT_TIMEZONE_STR = "Australia/Melbourne"
# TIMEZONE_STR = "America/Argentina/Buenos_Aires"
DEFAULT_TIMEZONE = ZoneInfo(DEFAULT_TIMEZONE_STR)
UTC = ZoneInfo("UTC")


def setRootLoggerLevel(level):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(max(level, handler.level))


def setup_logging(
    name_logger: str = "app",
    fmt: str=DEFAULT_LOG_FMT,
    timezone: ZoneInfo=DEFAULT_TIMEZONE,
    datefmt: str=LOG_DATE,
    colors: dict=DEFAULT_LOG_COLORS,
    indent: int=2,
    level=logging.INFO,
    rotating_file=None
) -> logging.Logger:
    """Setup a home-made logger with colored formatter and timezone support.
    """
    # get root logger (we will change this one!)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # clear old handlers

    # 0. Set the class of the root logger
    logging.setLoggerClass(IndentLogger)

    # 1. CONSOLE HANDLER: create a console hanlder with our formatting
    handler_console = logging.StreamHandler()
    handler_console.name = "console"
    formatter = IndentColorFormatter(
        fmt=fmt,
        log_colors=colors,
        timezone=timezone,
        indent=indent,
        datefmt=datefmt,
    )
    handler_console.setFormatter(formatter)
    root_logger.addHandler(handler_console)  # attach handler to root logger

    if rotating_file is not None:
        # 2. ROTATING FILE HANDLER: create a rotating file handler
        handler_file = RotatingFileHandler(
            rotating_file,          # log file name
            maxBytes=3 * 1024 * 1024,  # 3 MB
            backupCount=3       # keep last 5 rotated logs
        )
        # Optional: formatter
        # formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        handler_file.setFormatter(formatter)
        root_logger.addHandler(handler_file)    # attach handler to root logger

    # 3. FINALLY, build a logger with no handler and make it propagate
    log = logging.getLogger(name_logger)
    log.handlers.clear()  # clear old handlers
    log.setLevel(level)  # 👈 controls what records gets created at this logger
    # propagate up to the root logger! See doc about propagation and logger/handler levels
    log.propagate = True

    return log

##################################################
# Indent Colored Timezoned Logger & Formatter
##################################################
class IndentLogger(logging.Logger):
    """This improves the logger by adding a depth parameter depth to the log methods.
    Such parameter can then be used by the formatter to indent the message.

        e.g., log.info("message", depth=2)

    The depth parameter is optional and defaults to 0 (no indentation).
    It is added to the extra dictionary used by the formatter.
    """
    @override
    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        stacklevel=1,
        depth=0,
    ):
        if extra is None:
            extra = {}
        extra["depth"] = depth
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)

    @override
    def setLevel(self, level):
        super().setLevel(level)
        for handler in self.handlers:
            handler.setLevel(max(level, handler.level))


class IndentColorFormatter(ColoredFormatter):
    """This formatter adds:

        - indentation to the message based on the depth parameter.
        - colored formatter
        - llows setting a timezone for reporting dates and times
    """
    SHORT_LEVELS = {
        "WARNING": "WARN",
        "ERROR": "ERR",
        "CRITICAL": "CRIT",
        "DEBUG": "DEBG",
    }
    def __init__(self, *args, timezone=None, indent=2, **kwargs):
        super().__init__(*args, **kwargs)
        self.timezone = timezone
        self.indent = indent

    # alternative 1: add the indent to the message itself!
    # @override
    # def format(self, record):
    #     depth = getattr(record, "depth", 0)
    #     indent = "\t" * depth
    #     record.message = f"{indent}{record.getMessage()}"  # Add indent
    #     return super().format(record)

    # alternative 2: add the indent as data to the record
    @override
    def format(self, record):
        print(record.levelname)
        if record.levelname in self.SHORT_LEVELS:
            record.levelname = self.SHORT_LEVELS[record.levelname]
        record.indent = " " * self.indent * getattr(record, "depth", 0)
        return super().format(record)

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=self.timezone)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


# This is my formatter with special colors and timezone
#  ssardina - Sebastian Sardina - ssardina@gmail.com
# formatter_ssardina = IndentColorFormatter(
#     fmt=LOG_FMT_SIMPLE,
#     log_colors={
#         "DEBUG": "cyan",
#         "INFO": "green",
#         "WARNING": "yellow",
#         "ERROR": "red",
#         "CRITICAL": "bold_red",
#     },
#     timezone=TIMEZONE,
#     datefmt=LOG_DATE,
# )
