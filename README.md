# aws-security-tools

AWS security assessment tool for EC2, VPC, IAM, and S3 resources.

**Pipeline:** AWS CLI export → CloudFormation template → Checkov scan → CSV report (PASSED + FAILED)

## Quick Start (AWS CloudShell)

```bash
# 1. Clone the repository
git clone git@github.com:morakot-inta/aws-security-tools.git
cd aws-security-tools

# 2. Install dependencies (one-time)
bash setup.sh

# 3. Run assessment
./assess.sh
```

## Usage

```bash
./assess.sh                          # Use current CloudShell credentials & region
./assess.sh --region ap-southeast-1  # Override region
./assess.sh --output-dir /tmp/scan   # Custom output location
```

## Output

```
output/
├── raw/                    # Raw AWS CLI JSON exports
├── template/
│   └── cfn_template.json   # Generated CloudFormation template
├── checkov_result.json     # Checkov scan output
└── report_YYYYMMDD_HHMMSS.csv  # Final report
```

CSV columns: `Status, Check ID, Check Name, Resource Type, Resource Name, File Path, Severity, Guideline`

## Requirements

- AWS CLI (pre-installed in CloudShell)
- Python 3 (pre-installed in CloudShell)
- Checkov (`bash setup.sh` installs it)
