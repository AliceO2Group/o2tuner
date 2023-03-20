"""
O2Tuner exceptions
"""


class O2TunerError(Exception):
    """
    O2Tuner error class
    """

    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return self.msg


class O2TunerStopOptimisation(O2TunerError):
    """
    O2Tuner error class
    """


class O2TunerFatal(O2TunerError):
    """
    O2Tuner error class
    """
