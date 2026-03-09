#!/bin/bash
# scripts/export_aws.sh — Stage 1: Export AWS resources via CLI
# Called by assess.sh; expects OUTPUT_DIR env var to be set.
set -uo pipefail

RAW="$OUTPUT_DIR/raw"

# Helper: run an AWS CLI command, warn on failure but don't abort
aws_export() {
    local label="$1"; shift
    local outfile="$1"; shift
    echo "[export] $label..."
    if "$@" > "$outfile" 2>/tmp/aws_err; then
        local count
        count=$(python3 -c "
import json, sys
data = json.load(open('$outfile'))
vals = list(data.values())
print(len(vals[0]) if vals and isinstance(vals[0], list) else 1)
" 2>/dev/null || echo "?")
        echo "[export] $label — $count resource(s)"
    else
        echo "[WARN]   $label — failed ($(cat /tmp/aws_err | head -1))"
        echo "{}" > "$outfile"
    fi
}

# ── EC2 ───────────────────────────────────────────────────────────────────────
aws_export "EC2 Instances"       "$RAW/ec2_instances.json"       aws ec2 describe-instances --output json
aws_export "EC2 Security Groups" "$RAW/ec2_security_groups.json" aws ec2 describe-security-groups --output json
aws_export "EC2 Volumes"         "$RAW/ec2_volumes.json"         aws ec2 describe-volumes --output json

# ── VPC ───────────────────────────────────────────────────────────────────────
aws_export "VPCs"          "$RAW/vpc_vpcs.json"    aws ec2 describe-vpcs --output json
aws_export "Subnets"       "$RAW/vpc_subnets.json" aws ec2 describe-subnets --output json
aws_export "Network ACLs"  "$RAW/vpc_nacls.json"   aws ec2 describe-network-acls --output json
aws_export "Route Tables"  "$RAW/vpc_route_tables.json" aws ec2 describe-route-tables --output json


# ── RDS ───────────────────────────────────────────────────────────────────────
aws_export "RDS Instances" "$RAW/rds_instances.json" aws rds describe-db-instances --output json

# ── S3 (composite: list + per-bucket enrichment) ──────────────────────────────
echo "[export] S3 Buckets (with per-bucket enrichment)..."
python3 - <<'PYEOF'
import json, subprocess, os

raw = os.environ["OUTPUT_DIR"] + "/raw"

def aws(args):
    r = subprocess.run(["aws"] + args + ["--output", "json"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return json.loads(r.stdout)
    return None

buckets_resp = aws(["s3api", "list-buckets"])
buckets = buckets_resp.get("Buckets", []) if buckets_resp else []

for bucket in buckets:
    name = bucket["Name"]

    enc = aws(["s3api", "get-bucket-encryption", "--bucket", name])
    bucket["ServerSideEncryptionConfiguration"] = (
        enc.get("ServerSideEncryptionConfiguration") if enc else None
    )

    ver = aws(["s3api", "get-bucket-versioning", "--bucket", name])
    bucket["VersioningConfiguration"] = ver if ver else {}

    log = aws(["s3api", "get-bucket-logging", "--bucket", name])
    bucket["LoggingEnabled"] = log.get("LoggingEnabled") if log else None

    acl = aws(["s3api", "get-bucket-acl", "--bucket", name])
    bucket["Grants"] = acl.get("Grants", []) if acl else []

    pub = aws(["s3api", "get-public-access-block", "--bucket", name])
    bucket["PublicAccessBlockConfiguration"] = (
        pub.get("PublicAccessBlockConfiguration") if pub else None
    )

    pol_status = aws(["s3api", "get-bucket-policy-status", "--bucket", name])
    bucket["PolicyStatus"] = (
        pol_status.get("PolicyStatus") if pol_status else None
    )

with open(f"{raw}/s3_buckets.json", "w") as f:
    json.dump({"Buckets": buckets}, f, indent=2)

print(f"[export] S3 Buckets — {len(buckets)} bucket(s)")
PYEOF

echo "[export] All exports complete. Files in: $RAW"
