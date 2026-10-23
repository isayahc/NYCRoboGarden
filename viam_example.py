"""Compatibility entry point for the Viam inspection CLI."""

from viam_integration.__main__ import cli


if __name__ == "__main__":
    raise SystemExit(cli())
