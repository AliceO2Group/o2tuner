"""
O2Tuner module
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
