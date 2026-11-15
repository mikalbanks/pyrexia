#!/usr/bin/env python3
"""Verify a Pyrexia archive using reviewed checkout code, never archive code."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyrexia.evidence import verify_evidence  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/verify_evidence.py evidence.zip", file=sys.stderr)
        return 2
    try:
        result = verify_evidence(Path(sys.argv[1]).read_bytes())
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
