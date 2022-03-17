"""
Logging utils
"""


import sys
import colorama


class Log(object):
    """
    Logging class
    """

    def __init__(self):
        colorama.init()
        self.quiet = False

    def set_quiet(self, quiet=True):
        self.quiet = quiet

    def print_color(self, color_code, msg):
        if self.quiet:
            return
        sys.stderr.write(color_code)
        sys.stderr.write(msg)
        sys.stderr.write(colorama.Style.RESET_ALL)
        sys.stderr.write("\n")
        sys.stderr.flush()

    def debug(self, msg):
        self.print_color(colorama.Fore.MAGENTA, msg)

    def info(self, msg):
        self.print_color(colorama.Fore.GREEN, msg)

    def warning(self, msg):
        self.print_color(colorama.Fore.YELLOW, msg)

    def error(self, msg):
        self.print_color(colorama.Fore.RED, msg)
