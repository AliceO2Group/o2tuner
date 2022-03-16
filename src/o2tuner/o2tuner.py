"""
This is a dummy module for the moment
"""


class O2tuner(object):
    """
    Steering class for tuning
    """

    def __init__(self, handler) -> None:
        """
        Constructor is empty
        """
        self._handler = handler

    def reset_handler(self, handler):
        """
        Reset the handler
        """
        self._handler = handler

    def init(self, **kwargs):
        """
        Initialisation function
        """
        self._handler.initialise(**kwargs)

    def run(self):
        """
        Run optimisation
        """
        self._handler.optimise()
