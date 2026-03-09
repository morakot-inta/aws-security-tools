# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

AWS security assessment tool that exports live AWS resources via CLI, converts them to a CloudFormation template, scans with Checkov, and produces a CSV report showing both PASSED and FAILED checks.

Scope: EC2, VPC, S3, RDS.

## How to Run

```bash
# One-time setup (installs checkov via pip3 --user, CloudShell-compatible)
bash setup.sh

# Run full assessment — defaults to ap-southeast-1
./assess.sh

# Override region
./assess.sh --region us-east-1

# Output lands in output/report_YYYYMMDD_HHMMSS.csv
```

## Prerequisites

- AWS CloudShell (credentials auto-injected, `aws` and `python3` pre-installed)
- `checkov` — installed by `setup.sh` via `pip3 install checkov --user`
- `setup.sh` also adds `~/.local/bin` to `PATH` for the session

## Architecture — 4-Stage Pipeline

```
AWS Account
    │
    ▼
[Stage 1] scripts/export_aws.sh
  aws ec2/s3api describe/list → output/raw/*.json
    │
    ▼
[Stage 2] scripts/convert_to_cfn.py
  Raw JSON → output/template/cfn_template.json (CloudFormation format)
    │
    ▼
[Stage 3] scripts/run_checkov.sh
  checkov --framework cloudformation -o json → output/checkov_result.json
    │
    ▼
[Stage 4] scripts/generate_report.py
  Checkov JSON (passed_checks + failed_checks) → output/report_YYYYMMDD_HHMMSS.csv
```

### Why this design

- **CloudFormation as intermediate format**: Checkov has rich built-in CFN checks for EC2, VPC, and S3. The converter maps AWS CLI response field names to exact CFN property names so checks fire correctly.
- **Checkov `-o json` not `-o csv`**: Checkov's native CSV only includes failed checks. JSON output always contains both `passed_checks` and `failed_checks` arrays — Stage 4 reads both.
- **Python stdlib only**: No `pip install` required for the converter or reporter — only `json`, `csv`, `datetime` from stdlib.
- **S3 export is composite**: `list-buckets` gives names, then per-bucket calls (`get-bucket-encryption`, `get-bucket-versioning`, `get-bucket-logging`, `get-bucket-acl`, `get-public-access-block`) enrich the data before writing `output/raw/s3_buckets.json`.

### CSV Output Columns

```
Status, Check ID, Check Name, Resource Type, Resource Name, Severity, Guideline
```

Sorted: FAILED first, then PASSED, grouped by resource name, then check ID.

### CloudFormation Logical ID Convention

Resource IDs/names are sanitized to match `[A-Za-z0-9]+` (CFN requirement). Examples:
- EC2 instance `i-0abc123` → `EC2Instancei0abc123`
- S3 bucket `my-bucket` → `S3Bucketmybucket`

## Git Workflow

- Branch: `main` (push directly, no PRs needed)
- Remote: `git@github.com:morakot-inta/aws-security-tools.git`
- Commit format: `<type>: <short summary>` with `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- Push to GitHub after every logical commit
