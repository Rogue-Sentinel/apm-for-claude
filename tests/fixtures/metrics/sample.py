# HAND COUNT, counted by eye. Comments, docstrings, blank lines and lone-bracket lines are not logic;
# a multi-line string value counts on every line; "):" is logic because a colon is not a bracket.
# file 31
# function top_level 2
# function Shape.__init__ 1
# function Shape.area 1
# function Shape._hidden 2
# function Shape.label 3
# function Shape.label.inner 1
# function fetch 2
# function one_liner 1
# class Shape 2
"""Module docstring
over two lines."""
import os

CONFIG = {
    "key": "value",
    "other": [1, 2],
}

BANNER = """first
second { not code
third"""


def top_level(a, b):
    """Docstring over
    two lines."""
    # a comment with a { brace
    total = a + b
    return total


class Shape:
    """A shape."""

    kind = "shape"

    def __init__(self, side):
        self.side = side

    def area(self):
        return self.side ** 2

    def _hidden(self):
        return {
            "a": 1,
        }

    @property
    def label(self):
        def inner(text):
            return text.upper()
        return inner(self.kind)


async def fetch(
    url,
    timeout=5,
):
    data = await os.get(url)
    return data


def one_liner(x): return x
