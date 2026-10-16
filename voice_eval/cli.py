"""Command-line interface for the voice-agent evaluation playground."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluator import evaluate, load_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a JSONL file of voice-agent conversation traces.")
    parser.add_argument("trace_file", help="Path to a JSONL trace file")
    parser.add_argument("--out", help="Optional path for a JSON report")
    args = parser.parse_args()
    try:
        report = evaluate(load_jsonl(args.trace_file))
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            Path(args.out).write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return 0
    except (OSError, ValueError) as exc:
        print(f"voice-eval: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
