# Service Screener v2 — CloudShell Guide

**Tool:** [aws-samples/service-screener-v2](https://github.com/aws-samples/service-screener-v2)
**What it does:** Scans your AWS account across EC2, S3, IAM, RDS, and more — checks security, reliability, cost, and performance. Outputs an interactive HTML report.

---

## Prerequisites

Your IAM user/role needs these permissions:
- `ReadOnlyAccess` (AWS managed policy)
- `AWSCloudShellFullAccess`
- `cloudformation:CreateStack`
- `cloudformation:DeleteStack`

---

## Step 1 — Install (run once per CloudShell session)

```bash
cd /tmp
python3 -m venv .
source bin/activate
git clone https://github.com/aws-samples/service-screener-v2.git
cd service-screener-v2
pip install -r requirements.txt
alias screener='python3 /tmp/service-screener-v2/main.py'
```

> **Note:** CloudShell resets `/tmp` when the session ends. You must re-run these steps each new session.

---

## Step 2 — Run a Scan

### Scan all services in one region (most common)
```bash
screener --regions ap-southeast-1
```

### Scan specific services only
```bash
screener --regions ap-southeast-1 --services ec2,s3,rds,iam
```

### Scan multiple regions
```bash
screener --regions ap-southeast-1,us-east-1
```

### Scan all regions
```bash
screener --regions ALL
```

### Filter by tag (only scan tagged resources)
```bash
screener --regions ap-southeast-1 --tags env=prod
```

---

## Step 3 — Download the Report

When the scan finishes, it creates `output.zip` in the current directory.

**In CloudShell:**
1. Click **Actions** (top right) → **Download file**
2. Enter path: `/tmp/service-screener-v2/output.zip`
3. Click **Download**

Unzip on your computer and open `index.html` in a browser.

> **Security:** Do NOT host the HTML report on a public web server — it contains sensitive account information.

---

## Command Options Reference

| Option | Example | Description |
|---|---|---|
| `--regions` | `ap-southeast-1` | Region(s) to scan — required |
| `--services` | `ec2,s3,rds` | Limit to specific services |
| `--tags` | `env=prod` | Only scan resources with this tag |
| `--frameworks` | `AWS-WAF` | Filter by compliance framework |
| `--sequential` | _(flag)_ | Run services one at a time instead of parallel |
| `--workerCounts` | `4` | Number of parallel workers |
| `--debug` | _(flag)_ | Verbose output for troubleshooting |

### Available services
`ec2`, `s3`, `iam`, `rds`, `lambda`, `cloudfront`, `cloudtrail`, `cloudwatch`, `guardduty`, `eks`, `opensearch`, `redshift`, `sagemaker`, `sns`, `sqs`, `vpc`

---

## Expected Runtime

| Account size | Estimated time |
|---|---|
| Small (< 50 resources) | 2–5 min |
| Medium (50–200 resources) | 5–15 min |
| Large (200+ resources) | 15–30+ min |

---

## Troubleshooting

**`screener: command not found`**
Re-run the alias: `alias screener='python3 /tmp/service-screener-v2/main.py'`

**`No module named ...`**
Virtual environment not active: `source /tmp/bin/activate`

**Permission errors**
Ensure your IAM role has `ReadOnlyAccess` + the CloudFormation permissions listed above.

**Session expired / `/tmp` cleared**
Repeat Step 1 entirely — CloudShell resets `/tmp` after ~20 min of inactivity.
