#!/bin/bash
# scripts/run_checkov.sh — Stage 3: Run Checkov against the CFN template
# Usage: run_checkov.sh <template_file> <output_json>
set -uo pipefail

TEMPLATE_FILE="${1:?Template file path required}"
OUTPUT_JSON="${2:?Output JSON path required}"

# Ensure checkov is findable (CloudShell pip --user installs to ~/.local/bin)
export PATH="$HOME/.local/bin:$PATH"

if ! command -v checkov &>/dev/null; then
    echo "[ERROR] checkov not found. Run: pip3 install checkov --user" >&2
    exit 1
fi

if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "[ERROR] Template not found: $TEMPLATE_FILE" >&2
    exit 1
fi

echo "[checkov] Scanning: $TEMPLATE_FILE"

# --soft-fail        → always exit 0 (don't abort pipeline on findings)
# --framework        → only run CloudFormation checks
# -o json            → machine-readable output with passed + failed arrays
# --skip-download    → no Bridgecrew platform calls (no API key needed)
checkov \
    -f "$TEMPLATE_FILE" \
    --framework cloudformation \
    -o json \
    --soft-fail \
    --skip-download \
    --output-file-path "$(dirname "$OUTPUT_JSON")" \
    2>/tmp/checkov_stderr.log || true

# Checkov writes results_json.json into --output-file-path dir
CHECKOV_OUT="$(dirname "$OUTPUT_JSON")/results_json.json"

if [[ -f "$CHECKOV_OUT" ]]; then
    mv "$CHECKOV_OUT" "$OUTPUT_JSON"
    echo "[checkov] Results saved: $OUTPUT_JSON"
else
    # Fallback: capture stdout directly
    checkov \
        -f "$TEMPLATE_FILE" \
        --framework cloudformation \
        -o json \
        --soft-fail \
        --skip-download \
        2>/tmp/checkov_stderr.log > "$OUTPUT_JSON" || true
    echo "[checkov] Results saved (stdout): $OUTPUT_JSON"
fi

# Quick summary from the JSON
python3 - <<PYEOF
import json, sys
try:
    with open("$OUTPUT_JSON") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = data[0]
    results = data.get("results", {})
    passed = len(results.get("passed_checks", []))
    failed = len(results.get("failed_checks", []))
    print(f"[checkov] Summary — PASSED: {passed}, FAILED: {failed}")
except Exception as e:
    print(f"[checkov] Could not parse summary: {e}", file=sys.stderr)
PYEOF
