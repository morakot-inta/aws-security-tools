# AWS Security Findings — Remediation Guide

**Source:** Service Screener v2 — CPFINDINGS.csv
**Region:** ap-southeast-1 | **Total Findings:** 57

---

## Summary by Severity

| Severity | Count |
|---|---|
| 🔴 High | 26 |
| 🟠 Medium | 14 |
| 🟡 Low | 14 |
| ⚪ Informational | 3 |

---

## 🔴 HIGH — Fix Immediately

---

### IAM — MFA Not Enabled
**Check:** `mfaActive`
**Affected:** `Jusmin.p`, `natthakrit`, `natthida.j`

**Fix:**
1. AWS Console → IAM → Users → select user
2. **Security credentials** tab → Multi-factor authentication → **Assign MFA device**
3. Choose **Authenticator app** (Google Authenticator / Authy) or hardware key
4. Repeat for each user

---

### IAM — Full Admin Access (Least Privilege Violation)
**Check:** `FullAdminAccess`
**Affected:** `eks-deploy`, `Jusmin.p`, `morakot`, `natthakrit`, `natthida.j`, `cdk-hnb659fds-cfn-exec-role-*`

**Fix:**
1. AWS Console → IAM → Users/Roles → select each
2. **Permissions** tab → remove `AdministratorAccess` policy
3. Replace with specific policies based on job function:
   - Developer: `PowerUserAccess` + specific service policies
   - Read-only auditor: `ReadOnlyAccess`
   - EKS deploy: only `eks:*` + required ECR/S3 permissions
4. For CDK roles — review if `AdministratorAccess` is truly required or scope to specific CloudFormation resources

---

### IAM — Access Keys Not Rotated (90+ days)
**Check:** `hasAccessKeyNoRotate90days`
**Affected:** `eks-deploy`, `Jusmin.p`, `morakot`, `ses-smtp-user.20251102-155833`

**Fix:**
1. AWS Console → IAM → Users → select user → **Security credentials**
2. Create a **new access key** (note: max 2 per user)
3. Update the application/system using the old key with the new key
4. **Deactivate** the old key → confirm nothing breaks → **Delete** old key
5. Rotate every 90 days or use IAM Roles instead of long-lived keys where possible

> `ses-smtp-user` — update SMTP credentials in your mail application

---

### IAM — Users Inactive for 90+ Days
**Check:** `userNoActivity90days`
**Affected:** `eks-deploy`, `Jusmin.p`, `ses-smtp-user.20251102-155833`

**Fix:**
1. Confirm with the team if the user is still needed
2. If no longer needed → IAM → Users → **Delete user**
3. If needed but temporarily inactive → disable console access + deactivate access keys until required again

---

### IAM — AWS Config Not Enabled
**Check:** `EnableConfigService`
**Affected:** Account-level

**Fix:**
1. AWS Console → AWS Config → **Get started**
2. Select **Record all resources supported in this region**
3. Choose or create an S3 bucket for configuration history
4. Enable → costs ~$0.003 per configuration item recorded

---

### IAM — GuardDuty Not Enabled
**Check:** `enableGuardDuty`
**Affected:** Account-level

**Fix:**
1. AWS Console → GuardDuty → **Get started** → **Enable GuardDuty**
2. Free for 30 days, then ~$1–$4/month for small accounts
3. Optionally enable S3 Protection and EKS Protection

---

### IAM — No Alternate Contact Set
**Check:** `hasAlternateContact`
**Affected:** Account-level

**Fix:**
1. AWS Console → top-right account menu → **Account**
2. Scroll to **Alternate contacts**
3. Add contacts for **Billing**, **Operations**, and **Security** (name, email, phone)

---

### IAM — Password Not Changed in 365 Days
**Check:** `passwordLastChange365`
**Affected:** `natthakrit`

**Fix:**
1. IAM → Users → `natthakrit` → **Security credentials** → **Manage console password** → **Set a custom password**
2. Or contact the user to change their own password
3. Enforce via IAM password policy (max password age)

---

### EC2 — No IAM Instance Profile
**Check:** `EC2IamProfile`
**Affected:** `i-0f3b133fd6e687753`

**Fix:**
1. Create an IAM Role with EC2 as trusted entity + required permissions
2. AWS Console → EC2 → Instances → select instance
3. **Actions** → **Security** → **Modify IAM role** → attach the role
4. This removes the need for hardcoded credentials on the instance

---

### EC2 — Security Group: Sensitive Port Open to All
**Check:** `SGSensitivePortOpenToAll`
**Affected:** `sg-0395932079824097b`, `sg-0b9c3e57eb26113f9`

**Fix:**
1. EC2 → Security Groups → select SG → **Inbound rules** → **Edit**
2. Find rules with source `0.0.0.0/0` on sensitive ports (22/SSH, 3389/RDP, 3306/MySQL, 5432/PostgreSQL, etc.)
3. Change source to:
   - Your office IP: `YOUR.IP.ADDRESS/32`
   - Or a Bastion host security group ID
4. Delete or restrict the overly broad rule

---

### EC2 — Security Group: All Ports Open / Open to All
**Check:** `SGAllPortOpen`, `SGAllPortOpenToAll`
**Affected:** `sg-0b9c3e57eb26113f9`

**Fix:**
1. EC2 → Security Groups → `sg-0b9c3e57eb26113f9` → **Inbound rules** → **Edit**
2. Remove any rule with **Port range: All** and source `0.0.0.0/0`
3. Replace with specific ports only (e.g., 443 for HTTPS, 80 for HTTP)
4. Use the principle: only open what's needed

---

### EC2 — Security Group: No Encryption in Transit
**Check:** `SGEncryptionInTransit`
**Affected:** `sg-0b9c3e57eb26113f9`

**Fix:**
1. Ensure services behind this SG use HTTPS/TLS (port 443) not plain HTTP (80)
2. Update the SG to allow only port 443 inbound (remove port 80 if possible)
3. On the application side, enable SSL/TLS certificate

---

### EC2 — VPC Flow Logs Not Enabled
**Check:** `VPCFlowLogEnabled`
**Affected:** `vpc-0a092489c42e8be2f`

**Fix:**
1. AWS Console → VPC → Your VPCs → select VPC
2. **Flow logs** tab → **Create flow log**
3. Filter: **All** (accepted + rejected)
4. Destination: **CloudWatch Logs** (create a new log group `/vpc/flowlogs`)
5. IAM Role: create new or use existing role with CloudWatch permissions
6. Cost: ~$0.50/GB ingested to CloudWatch

---

### RDS — Engine Major Version Outdated
**Check:** `EngineVersionMajor`
**Affected:** `database-1` (PostgreSQL)

**Fix:**
1. Check current version: RDS → Databases → database-1 → **Configuration**
2. Take a manual snapshot first (RDS → Snapshots → **Take snapshot**)
3. RDS → database-1 → **Modify** → **DB engine version** → select latest major version
4. Apply **During next scheduled maintenance window** (safer) or **Immediately**
5. Test application compatibility before upgrading production

---

### RDS — Publicly Accessible
**Check:** `PubliclyAccessible`
**Affected:** `database-1`

**Fix:**
1. RDS → Databases → database-1 → **Modify**
2. **Connectivity** section → **Publicly accessible** → set to **No**
3. Apply during maintenance window
4. Ensure your application connects via private VPC endpoint or within the same VPC

---

---

## 🟠 MEDIUM — Fix Soon

---

### IAM — Passwords Not Changed in 90 Days
**Check:** `passwordLastChange90`
**Affected:** `root_id`, `Jusmin.p`, `morakot`, `natthida.j`

**Fix for root:** AWS Console → account menu → **Security credentials** → change root password + ensure MFA is on root
**Fix for IAM users:** IAM → Users → Security credentials → reset password
**Long-term:** Set IAM password policy to force rotation every 90 days:
- IAM → Account settings → **Edit password policy** → Maximum password age: 90 days

---

### IAM — Console Not Accessed in 90 Days
**Check:** `consoleLastAccess90`
**Affected:** `root_id`, `Jusmin.p`, `natthakrit`

**Fix:**
- `root_id` — Root account should almost never be used. Keep it locked away with MFA only. This is expected.
- `Jusmin.p`, `natthakrit` — If users no longer need console access, remove it: IAM → user → **Security credentials** → **Manage console password** → **Disable console access**

---

### EC2 — Instance Auto-Assigns Public IP
**Check:** `EC2InstanceAutoPublicIP`
**Affected:** `i-0f3b133fd6e687753`

**Fix:**
- For the subnet: VPC → Subnets → select → **Actions** → **Edit subnet settings** → uncheck **Enable auto-assign public IPv4 address**
- Place the instance in a private subnet and use a NAT Gateway for outbound internet access
- Use ALB/NLB in a public subnet to route traffic to private instances

---

### RDS — Engine Minor Version Not Latest
**Check:** `EngineVersionMinor`
**Affected:** `database-1`

**Fix:**
1. RDS → database-1 → **Modify** → update to latest minor version
2. Or enable **Auto minor version upgrade** on the instance so it applies automatically during maintenance windows

---

### RDS — Using Default Security Group
**Check:** `SecurityGroupDefault`
**Affected:** `sg-0b9c3e57eb26113f9`

**Fix:**
1. Create a dedicated security group for RDS: EC2 → Security Groups → **Create security group**
2. Add inbound rule: PostgreSQL (5432) — source: only the application server's SG
3. RDS → database-1 → **Modify** → **Connectivity** → change to the new dedicated SG
4. Remove the default SG from the RDS instance

---

### S3 — MFA Delete Not Enabled
**Check:** `MFADelete`
**Affected:** `cdk-hnb659fds-assets-*`, `terrafrom-backend-surveyor`

**Fix (requires root credentials or aws CLI):**
```bash
aws s3api put-bucket-versioning \
  --bucket BUCKET_NAME \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::ACCOUNT_ID:mfa/root-account-mfa CURRENT_MFA_CODE"
```
> Note: MFA Delete can only be enabled by root account. Primarily recommended for critical data buckets like `terrafrom-backend-surveyor`.

---

### S3 — TLS Not Enforced on Bucket Policy
**Check:** `TlsEnforced`
**Affected:** `terrafrom-backend-surveyor`

**Fix:** Add a bucket policy that denies HTTP requests:
1. S3 → `terrafrom-backend-surveyor` → **Permissions** → **Bucket policy** → **Edit**
2. Add this policy (merge with existing if any):
```json
{
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": [
    "arn:aws:s3:::terrafrom-backend-surveyor",
    "arn:aws:s3:::terrafrom-backend-surveyor/*"
  ],
  "Condition": {
    "Bool": { "aws:SecureTransport": "false" }
  }
}
```

---

---

## 🟡 LOW — Plan to Fix

---

### EC2 — Instance Has Public IP
**Check:** `EC2InstancePublicIP`
**Affected:** `i-0f3b133fd6e687753`

**Fix:** Move instance to a private subnet. Use Load Balancer or NAT Gateway for access.

---

### EC2 — Subnet Auto-Assigns Public IP
**Check:** `EC2SubnetAutoPublicIP`
**Affected:** subnet of `i-0f3b133fd6e687753`

**Fix:** VPC → Subnets → select subnet → **Actions** → **Edit subnet settings** → disable **Auto-assign public IPv4**

---

### EC2 — EBS Volume Not Encrypted
**Check:** `EBSEncrypted`
**Affected:** `vol-02f576b9641ff0030`

**Fix:**
1. Create a snapshot: EC2 → Volumes → select → **Actions** → **Create snapshot**
2. From the snapshot, create an encrypted copy: Snapshots → select → **Actions** → **Copy snapshot** → enable encryption
3. Create a new volume from the encrypted snapshot
4. Stop the instance → detach old volume → attach new encrypted volume → start instance
5. Or enable **EBS encryption by default** for new volumes: EC2 → Settings → **Data protection and security** → Enable EBS encryption

---

### EC2 — Default Security Group Allows Traffic
**Check:** `SGDefaultDisallowTraffic`
**Affected:** `sg-0b9c3e57eb26113f9`

**Fix:** EC2 → Security Groups → default SG → remove all inbound and outbound rules. Never attach resources to the default SG.

---

### IAM — Weak Password Policy
**Check:** `passwordPolicy`
**Affected:** Account-level

**Fix:** IAM → Account settings → **Edit password policy** → enable:
- Minimum length: 14 characters
- Require uppercase, lowercase, numbers, symbols
- Max age: 90 days
- Prevent reuse: last 5 passwords

---

### RDS — Using Default Master Admin Name
**Check:** `DefaultMasterAdmin`
**Affected:** `database-1`

**Fix:** Cannot rename the master user after creation. For new databases, avoid common names like `admin`, `postgres`, `root`. Use a custom name. Document for your next database provisioning.

---

### S3 — ACL Enabled (Should Use Bucket Policies Instead)
**Check:** `AccessControlList`
**Affected:** `cdk-hnb659fds-assets-*`, `terrafrom-backend-surveyor`

**Fix:** S3 → bucket → **Permissions** → **Object Ownership** → set to **Bucket owner enforced** (disables ACLs). Use bucket policies for access control instead.

---

### S3 — Access Logging Not Enabled
**Check:** `BucketLogging`
**Affected:** `cdk-hnb659fds-assets-*`, `terrafrom-backend-surveyor`

**Fix:**
1. Create a dedicated logging bucket (e.g., `my-s3-access-logs`)
2. S3 → target bucket → **Properties** → **Server access logging** → **Enable**
3. Set target bucket to the logging bucket

---

### S3 — Macie Not Enabled
**Check:** `MacieToEnable`
**Affected:** Account-level

**Fix:** AWS Console → Macie → **Get started** → **Enable Macie**. Scans S3 buckets for sensitive data (PII, credentials). Costs based on data scanned.

---

## ⚪ INFORMATIONAL

---

### S3 — Object Lock Not Enabled
**Check:** `ObjectLock`
**Affected:** `cdk-hnb659fds-assets-*`, `terrafrom-backend-surveyor`

Object Lock prevents objects from being deleted or overwritten for a defined period (WORM — Write Once Read Many). Only enable if you have compliance/audit requirements.
**Note:** Object Lock can only be enabled at bucket creation time.

---

## Recommended Fix Order

| Priority | Action |
|---|---|
| 1 | Enable MFA for all IAM users (`Jusmin.p`, `natthakrit`, `natthida.j`) |
| 2 | Enable GuardDuty |
| 3 | Restrict Security Groups (remove open-to-all rules) |
| 4 | Make RDS non-publicly accessible |
| 5 | Remove FullAdminAccess — apply least privilege |
| 6 | Rotate access keys older than 90 days |
| 7 | Enable VPC Flow Logs |
| 8 | Enable AWS Config |
| 9 | Upgrade RDS PostgreSQL major version |
| 10 | Enable AWS Config alternate contacts |
