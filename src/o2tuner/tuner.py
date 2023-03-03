"""
O2Tuner module
"""


from o2tuner.log import Log

LOG = Log()


class O2TunerError(Exception):
    """
    O2Tuner error class
    """

    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return self.msg
