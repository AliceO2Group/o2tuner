"""
Common system tools
"""
import sys


class AttrHolder:
    """
    Simply hold some attributes
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def add(self, key, value):
        """
        Add an attribute
        """
        if self.has(key):
            print(f"Adding system object {key} which exists already.")
            sys.exit(1)
        setattr(self, key, value)

    def has(self, key):
        """
        Check if some attribute is set
        """
        return hasattr(self, key)

    def get(self, key, *args):
        """
        Get an attribute
        """
        if len(args) > 1:
            print("Accepting exactly one default value.")
        if not self.has(key):
            if args:
                return args[0]
            print(f"System object {key} unknown.")
            sys.exit(1)
        return getattr(self, key)


# An object that simply holds other central objects as attributes
SYSTEM_OBJECTS = AttrHolder()


def add_system_attr(key, value):
    """
    Add a system-wide attribute
    """
    SYSTEM_OBJECTS.add(key, value)


def get_system_attr(key, *args):
    """
    Add a system-wide attribute
    """
    return SYSTEM_OBJECTS.get(key, *args)
