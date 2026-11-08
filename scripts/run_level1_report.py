#!/usr/bin/env python3
"""Generate a complete offline supplier operations report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supplier_report import build_supplier_report_from_files, write_csv, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--invoices", required=True)
    parser.add_argument("--operations", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--csv", help="optional CSV export path")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    report = build_supplier_report_from_files(
        policy_path=args.policy,
        invoices_path=args.invoices,
        operations_path=args.operations,
        report_id=args.report_id,
        observed_at=args.observed_at,
    )
    write_report(args.report, report)
    if args.csv:
        write_csv(args.csv, report)
    print(json.dumps({"ok": True, "report": args.report, "metrics": report["metrics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
