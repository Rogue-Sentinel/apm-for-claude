"""Errors the apm command line reports as one line for the user."""
from __future__ import annotations


class UsageError(Exception):
    """The command cannot run here; the message is one line for the user."""


class DebtError(UsageError):
    """The debt baseline, a checker or a git ref cannot be used; the message is one line for the user."""
