import logging
from settings import *


# A formatter which outputs colors
class ColoredFormatter(logging.Formatter):
    grey     = "\x1b[38;21m"
    yellow   = "\x1b[33;21m"
    blueish  = "\x1b[33;36m"
    red      = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset    = "\x1b[0m"

    FORMATS = {
        logging.DEBUG:    grey     + LOG_FORMAT + reset,
        logging.INFO:     blueish  + LOG_FORMAT + reset,
        logging.WARNING:  yellow   + LOG_FORMAT + reset,
        logging.ERROR:    red      + LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + LOG_FORMAT + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(
            log_fmt,
            style="{",
            datefmt=LOG_TIME_FORMAT
        )
        return formatter.format(record)


# Create the logger
globalLog = logging.getLogger(__name__)
globalLog.setLevel(LOG_LEVEL)

# Create a console handler and add it to the logger
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(LOG_LEVEL)
if USE_LOG_COLORS:
    consoleHandler.setFormatter(ColoredFormatter())
else:
    consoleHandler.setFormatter(
        logging.Formatter(LOG_FORMAT, datefmt=LOG_TIME_FORMAT, style='{')
    )
globalLog.addHandler(consoleHandler)

# Create a file handler and add it to the logger
if LOG_TO_FILE:
    fileHandler = logging.FileHandler(LOG_FILE)
    fileHandler.setFormatter(
        logging.Formatter(LOG_FORMAT, datefmt=LOG_TIME_FORMAT, style='{')
    )
    globalLog.addHandler(fileHandler)
