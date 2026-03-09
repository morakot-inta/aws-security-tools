#!/usr/bin/env python3
"""
scripts/generate_report.py — Stage 4
Parses Checkov JSON output and produces a CSV report with both PASSED and FAILED checks.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime


CSV_HEADERS = [
    "Status",
    "Check ID",
    "Check Name",
    "Resource Type",
    "Resource Name",
    "File Path",
    "Severity",
    "Guideline",
]


def resource_type_from_resource(resource_str):
    """
    Checkov resource field format: 'AWS::S3::Bucket.MyBucketName'
    Returns ('AWS::S3::Bucket', 'MyBucketName')
    """
    if "." in resource_str:
        parts = resource_str.split(".", 1)
        return parts[0], parts[1]
    return resource_str, resource_str


def parse_check(check, status):
    resource_str = check.get("resource", "")
    resource_type, resource_name = resource_type_from_resource(resource_str)

    return {
        "Status": status,
        "Check ID": check.get("check_id", ""),
        "Check Name": check.get("check_name", ""),
        "Resource Type": resource_type,
        "Resource Name": resource_name,
        "File Path": check.get("file_path", ""),
        "Severity": check.get("severity") or "",
        "Guideline": check.get("guideline") or "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkov-result", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.checkov_result):
        print(f"[ERROR] Checkov result not found: {args.checkov_result}", file=sys.stderr)
        sys.exit(1)

    with open(args.checkov_result) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse Checkov JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Checkov JSON can be a list (one entry per framework) or a single dict
    if isinstance(data, list):
        data = data[0] if data else {}

    results = data.get("results", {})
    passed_checks = results.get("passed_checks", [])
    failed_checks = results.get("failed_checks", [])

    rows = []
    for check in failed_checks:
        rows.append(parse_check(check, "FAILED"))
    for check in passed_checks:
        rows.append(parse_check(check, "PASSED"))

    # Sort: FAILED first, then by resource name, then check ID
    rows.sort(key=lambda r: (
        0 if r["Status"] == "FAILED" else 1,
        r["Resource Name"],
        r["Check ID"],
    ))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(args.output_dir, f"report_{timestamp}.csv")

    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    failed_count = sum(1 for r in rows if r["Status"] == "FAILED")
    passed_count = sum(1 for r in rows if r["Status"] == "PASSED")
    print(f"[report] FAILED: {failed_count} | PASSED: {passed_count} | Total: {len(rows)}", file=sys.stderr)

    # Print path to stdout so assess.sh can capture it
    print(report_path)


if __name__ == "__main__":
    main()
