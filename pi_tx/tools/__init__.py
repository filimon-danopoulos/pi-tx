"""Utility CLI subcommands.

Usage:
  python -m pi_tx.tools <command> [args]

Commands:
  create-model   Interactive model JSON creator
  map-stick      Interactive joystick mapping tool (stick_mapping.json)
"""

from __future__ import annotations
import sys

from . import create_model as _create_model
from . import map_stick as _map_stick

COMMANDS = {
    "create-model": lambda argv: _create_model.main(argv),
    "map-stick": lambda argv: _map_stick.main(argv),
}


def main(argv: list[str] | None = None):  # pragma: no cover
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__.strip())
        print("\nAvailable:")
        for name in sorted(COMMANDS):
            print(f"  {name}")
        return 0
    cmd = argv[0]
    handler = COMMANDS.get(cmd)
    if not handler:
        print(f"Unknown command: {cmd}\nUse --help to list")
        return 1
    return handler(argv[1:])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
