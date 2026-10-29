"""Command line entry point."""
import argparse
import json
import sys
from . import __version__
from .audit import audit

def main(argv=None):
    parser = argparse.ArgumentParser(description="Check documented picture-word claims against Python code.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--ignore", action="append", default=[])
    parser.add_argument("--fail-on", choices=["HIGH", "MEDIUM"], default="HIGH")
    parser.add_argument("--version", action="version", version=__version__)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    try:
        result = audit(args.root, args.ignore, args.fail_on)
    except (ValueError, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result))
    else:
        print(result["verdict"])
        for finding in result["findings"]:
            print("{severity} {rule}: {message}".format(**finding))
        if args.verbose:
            print("Scanned {} Python files".format(result["scanned_python_files"]))
    return 2 if result["verdict"] == "FAIL" else 0

if __name__ == "__main__":
    sys.exit(main())
