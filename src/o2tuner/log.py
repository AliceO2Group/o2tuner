"""
Logging utils
"""


import logging
from copy import copy

from o2tuner.bookkeeping import get_system_attr, add_system_attr


# We want to have something that appends without giving level (and potentially additional fields)
LOGGING_APPEND_NUMBER = 60
logging.addLevelName(LOGGING_APPEND_NUMBER, "APPEND")


def append_log(self, message, *args, **kws):
    """
    Function for appending to previous logging
    """
    if self.isEnabledFor(LOGGING_APPEND_NUMBER):
        # disable pylint warning for a good reason so that we can implement one of our own log levels
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOGGING_APPEND_NUMBER, message, args, **kws)  # pylint: disable=protected-access


# add function for custom logging
logging.Logger.append_log = append_log


LOGGER_NAME = "O2TunerLogger"
LOGGING_PREFIX = "O2T-"


class O2TunerLoggerFormatter(logging.Formatter):
    """
    A custom formatter that colors the levelname on request
    """

    # color names to indices
    color_map = {
        'black': 0,
        'red': 1,
        'green': 2,
        'yellow': 3,
        'blue': 4,
        'magenta': 5,
        'cyan': 6,
        'white': 7,
    }

    level_map = {
        # background color, foreground color, bold
        logging.DEBUG: (None, 'blue', False),
        logging.INFO: (None, 'green', False),
        logging.WARNING: (None, 'magenta', False),
        logging.ERROR: (None, 'red', False),
        logging.CRITICAL: ('red', 'white', True),
        LOGGING_APPEND_NUMBER: (None, None, False)
    }
    # start and end formatting
    csi = '\x1b['
    reset = '\x1b[0m'

    # Define default format string
    def __init__(self, verbosity=0, datefmt=None, style='%', color=False):
        logging.Formatter.__init__(self, "", datefmt, style)

        self.color = color
        # to align everything with the length of the log-level names
        try:
            self.loglevel_names = logging.getLevelNamesMapping().keys()
        except AttributeError:
            # Above function only exists for Python >= 3.11, to be refined in the future
            self.loglevel_names = list(logging._nameToLevel.keys())  # pylint: disable=protected-access

        self.prefix = None
        self.guarantee_n_letters = None
        # format string per verbosity
        self.verbosity_fmt_map = None
        # how to handle append per verbosity
        self.verbosity_append_fmt = None
        # how to replace linebreaks
        self.replace_linebreaks = None
        # add formats
        self.verbosity = None
        self.default_formatter = None
        self.append_formatter = None

        self.initialise(verbosity=verbosity, datefmt=datefmt, style=style)

    def initialise(self, prefix=LOGGING_PREFIX, verbosity=0, datefmt=None, style="%"):
        """
        Initialise for pretty logging
        """
        self.prefix = prefix
        self.guarantee_n_letters = len(self.prefix) + max(len(name) for name in self.loglevel_names)
        # format string per verbosity
        self.verbosity_fmt_map = ["%(levelname)s: %(message)s", "%(levelname)s in %(pathname)s:%(lineno)d:\n%(message)s"]
        # how to handle append per verbosity
        self.verbosity_append_fmt = [f"{' ':{self.guarantee_n_letters}}: %(message)s", "%(message)s"]
        # how to replace linebreaks
        self.replace_linebreaks = [f"\n{' ':{self.guarantee_n_letters}}: ", "\n"]
        # add formats
        self.verbosity = max(0, min(len(self.verbosity_fmt_map) - 1, verbosity))
        logging.Formatter.__init__(self, self.verbosity_fmt_map[self.verbosity], datefmt, style)
        self.default_formatter = logging.Formatter(self.verbosity_fmt_map[self.verbosity], datefmt, style)
        self.append_formatter = logging.Formatter(self.verbosity_append_fmt[self.verbosity], datefmt, style)

    def log_for_worker(self, worker_id):
        """
        At the moment, this leads to prepending a different prefix
        """
        self.initialise(f"{LOGGING_PREFIX}W{worker_id}-", self.verbosity)

    def format(self, record):
        """
        Derived format implementation
        """
        # Copy the record so the global format is kept
        cached_record = copy(record)
        requ_color = self.color
        # Could be a lambda so check for callable property
        if callable(self.color):
            requ_color = self.color()

        # replace \n to nicely align everything, not needed for verbosity 1
        cached_record.msg = cached_record.msg.replace("\n", self.replace_linebreaks[self.verbosity])

        if cached_record.levelno != LOGGING_APPEND_NUMBER:
            levelname = self.prefix + cached_record.levelname
            cached_record.levelname = f"{levelname:{self.guarantee_n_letters}}"

        # Colorize if requested
        if record.levelno in self.level_map and requ_color:
            bgc, fgc, bold = self.level_map[record.levelno]
            params = []
            if bgc in self.color_map:
                params.append(str(self.color_map[bgc] + 40))
            if fgc in self.color_map:
                params.append(str(self.color_map[fgc] + 30))
            if bold:
                params.append('1')
            if params:
                cached_record.levelname = "".join((self.csi, ';'.join(params), "m",
                                                   cached_record.levelname,
                                                   self.reset))

        if cached_record.levelno == LOGGING_APPEND_NUMBER:
            return self.append_formatter.format(cached_record)

        return self.default_formatter.format(cached_record)


def configure_logger(debug=False, verbosity=0, logfile=None):
    """
    Basic configuration adding a custom formatted StreamHandler and turning on
    debug info if requested.
    """
    logger = logging.getLogger(LOGGER_NAME)

    if not get_system_attr("logging_streamhandler", None):
        # Turn on debug info only on request
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        stream_handler = logging.StreamHandler()
        formatter = O2TunerLoggerFormatter(verbosity=verbosity,
                                           color=lambda: getattr(stream_handler.stream, 'isatty', None))

        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        add_system_attr("logging_streamhandler", stream_handler)

    if logfile is not None and not get_system_attr("logging_filehandler", None):
        # Specify output format
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(O2TunerLoggerFormatter())
        logger.addHandler(file_handler)
        add_system_attr("logging_filehandler", file_handler)


def log_on_worker(worker_id):
    """
    Notify that this is logging on a worker
    """
    stream_handler = get_system_attr("logging_streamhandler", None)
    if not stream_handler:
        return

    formatter = stream_handler.formatter
    formatter.log_for_worker(worker_id)


def get_logger():
    """
    Get the global logger for this package and set handler together with formatters.
    """
    return logging.getLogger(LOGGER_NAME)
