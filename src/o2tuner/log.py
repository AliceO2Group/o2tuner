"""
Logging utils
"""


import sys
import colorama


class Log:
    """
    Logging class
    """

    def __init__(self):
        colorama.init()
        self.quiet = False

    def set_quiet(self, quiet=True):
        """
        En-/disable logging messages
        """
        self.quiet = quiet

    def print_color(self, color_code, msg):
        """
        Implementation of logging
        """
        if self.quiet:
            return
        sys.stderr.write(color_code)
        sys.stderr.write(msg)
        sys.stderr.write(colorama.Style.RESET_ALL)
        sys.stderr.write("\n")
        sys.stderr.flush()

    def debug(self, msg):
        """
        Wrapper for debug messages
        """
        self.print_color(colorama.Fore.MAGENTA, "[DEBUG]: " + msg)

    def info(self, msg):
        """
        Wrapper for info messages
        """
        self.print_color(colorama.Fore.GREEN, "[INFO]: " + msg)

    def warning(self, msg):
        """
        Wrapper for warning messages
        """
        self.print_color(colorama.Fore.YELLOW, "[WARNING]: " + msg)

    def error(self, msg):
        """
        Wrapper for error messages
        """
        self.print_color(colorama.Fore.RED, "[ERROR]: " + msg)
