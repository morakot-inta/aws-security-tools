#!/bin/bash
# assess.sh — AWS Security Assessment Tool (CloudShell-compatible)
# Usage: ./assess.sh [--region REGION] [--output-dir DIR]
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
REGION="ap-southeast-1"
OUTPUT_DIR="$(pwd)/output"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)    REGION="$2";     shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# ── Ensure ~/.local/bin is in PATH (CloudShell pip --user installs go here) ──
export PATH="$HOME/.local/bin:$PATH"

# ── Set region if provided ────────────────────────────────────────────────────
if [[ -n "$REGION" ]]; then
    export AWS_DEFAULT_REGION="$REGION"
fi

# ── Prerequisite checks ───────────────────────────────────────────────────────
echo "[assess] Checking prerequisites..."
for cmd in aws python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "[ERROR] '$cmd' not found." >&2
        exit 1
    fi
done

if ! command -v checkov &>/dev/null; then
    echo "[assess] checkov not found — installing via pip3..."
    pip3 install checkov --user -q
    echo "[assess] checkov installed."
fi

# ── Show active identity ──────────────────────────────────────────────────────
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
ACTIVE_REGION=$(aws configure get region 2>/dev/null || echo "${AWS_DEFAULT_REGION:-us-east-1}")
echo "[assess] Account : $ACCOUNT"
echo "[assess] Region  : $ACTIVE_REGION"

# ── Create output directories ─────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR/raw" "$OUTPUT_DIR/template"
export OUTPUT_DIR

# ── Stage 1: Export AWS resources ─────────────────────────────────────────────
echo ""
echo "[assess] ── Stage 1: Exporting AWS resources ──"
bash "$SCRIPT_DIR/scripts/export_aws.sh"

# ── Stage 2: Convert to CloudFormation ────────────────────────────────────────
echo ""
echo "[assess] ── Stage 2: Converting to CloudFormation template ──"
python3 "$SCRIPT_DIR/scripts/convert_to_cfn.py" \
    --raw-dir "$OUTPUT_DIR/raw" \
    --output "$OUTPUT_DIR/template/cfn_template.json"

# ── Stage 3: Run Checkov ──────────────────────────────────────────────────────
echo ""
echo "[assess] ── Stage 3: Running Checkov scan ──"
bash "$SCRIPT_DIR/scripts/run_checkov.sh" \
    "$OUTPUT_DIR/template/cfn_template.json" \
    "$OUTPUT_DIR/checkov_result.json"

# ── Stage 4: Generate CSV report ──────────────────────────────────────────────
echo ""
echo "[assess] ── Stage 4: Generating CSV report ──"
REPORT=$(python3 "$SCRIPT_DIR/scripts/generate_report.py" \
    --checkov-result "$OUTPUT_DIR/checkov_result.json" \
    --output-dir "$OUTPUT_DIR")

# ── Stage 5: Generate HTML dashboard ──────────────────────────────────────────
echo ""
echo "[assess] ── Stage 5: Generating HTML dashboard ──"
DASHBOARD=$(python3 "$SCRIPT_DIR/scripts/generate_html.py" \
    --csv "$REPORT" \
    --output-dir "$OUTPUT_DIR")

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Assessment complete"
echo " CSV     : $REPORT"
echo " HTML    : $DASHBOARD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
