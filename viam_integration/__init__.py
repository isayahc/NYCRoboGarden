"""Reusable Viam connectivity and read-only hardware inspection."""

from .client import connect, inspect_machine

__all__ = ["connect", "inspect_machine"]
