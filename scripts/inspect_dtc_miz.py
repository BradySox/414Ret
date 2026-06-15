from __future__ import annotations

import argparse
from pathlib import Path

from game.missiongenerator.dtc.diagnostics import (
    diff_miz_dtc,
    format_summaries,
    inspect_miz_dtc,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or diff native DTC cartridges embedded in .miz files."
    )
    parser.add_argument("miz", type=Path, help="Path to the .miz to inspect")
    parser.add_argument(
        "--compare",
        type=Path,
        help="Optional second .miz. When set, print DTC JSON diffs as well.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Maximum number of diff lines to print when using --compare",
    )
    args = parser.parse_args()

    print(f"Inspecting {args.miz}")
    for line in format_summaries(inspect_miz_dtc(args.miz)):
        print(line)

    if args.compare is not None:
        print()
        print(f"Comparing against {args.compare}")
        diffs = diff_miz_dtc(args.miz, args.compare, limit=args.limit)
        if not diffs:
            print("No DTC JSON differences found.")
        else:
            for diff in diffs:
                print(diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
