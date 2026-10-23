"""Connect to Viam and inspect resources without moving hardware."""

import argparse
import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv

from . import inspect_machine


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Only verify connection and list resources")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    try:
        return asyncio.run(inspect_machine(list_only=args.list))
    except TimeoutError:
        sys.exit("Viam connection timed out after 30 seconds. Check machine status and network access.")
    except Exception as exc:
        sys.exit(f"Viam connection failed: {exc}")


if __name__ == "__main__":
    sys.exit(cli())
