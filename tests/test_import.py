"""
Module used to test if installation is successful
"""


from o2tuner import o2tuner


def add(val):
    """
    I add
    """
    return o2tuner.add_one(val)


def test_add():
    """
    Test add_one existence
    """
    assert add(42) == 43
