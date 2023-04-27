"""
To test the full o2tuner chain
"""


def evaluate(inspectors, config):
    """
    A dummy objective
    """
    # in this example we know that we have an inspector, otherwise we should check
    inspector = inspectors[0]
    print(inspector.get_losses())
    print(config)
    return True
