#!/usr/bin/env python3
"""
scripts/convert_to_cfn.py — Stage 2
Converts raw AWS CLI JSON exports to a CloudFormation template (JSON format).
Checkov uses CloudFormation property names, so mappings must be exact.
"""
import argparse
import json
import os
import re
import sys


def sanitize_id(prefix, raw_id):
    """CloudFormation logical IDs must match [A-Za-z0-9]+."""
    clean = re.sub(r"[^A-Za-z0-9]", "", raw_id)
    return f"{prefix}{clean}"


def load(raw_dir, filename):
    path = os.path.join(raw_dir, filename)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


# ── EC2 Instances ─────────────────────────────────────────────────────────────
def convert_ec2_instances(data, resources):
    for reservation in data.get("Reservations", []):
        for inst in reservation.get("Instances", []):
            iid = inst.get("InstanceId", "unknown")
            logical_id = sanitize_id("EC2Instance", iid)

            props = {
                "ImageId": inst.get("ImageId", ""),
                "InstanceType": inst.get("InstanceType", ""),
            }

            # IMDSv2 check (CKV_AWS_79)
            meta = inst.get("MetadataOptions", {})
            if meta:
                props["MetadataOptions"] = {
                    "HttpTokens": meta.get("HttpTokens", "optional"),
                    "HttpEndpoint": meta.get("HttpEndpoint", "enabled"),
                }

            # Monitoring (CKV_AWS_8)
            if inst.get("Monitoring", {}).get("State") == "enabled":
                props["Monitoring"] = True

            # EBS root volume encryption (CKV_AWS_8)
            block_mappings = inst.get("BlockDeviceMappings", [])
            if block_mappings:
                props["BlockDeviceMappings"] = [
                    {
                        "DeviceName": bdm.get("DeviceName", ""),
                        "Ebs": {
                            "Encrypted": bdm.get("Ebs", {}).get("DeleteOnTermination", False),
                            "DeleteOnTermination": bdm.get("Ebs", {}).get("DeleteOnTermination", True),
                        },
                    }
                    for bdm in block_mappings
                    if "Ebs" in bdm
                ]

            # Network — public IP assignment
            nics = inst.get("NetworkInterfaces", [])
            if nics:
                props["NetworkInterfaces"] = [
                    {
                        "AssociatePublicIpAddress": bool(
                            nic.get("Association", {}).get("PublicIp")
                        ),
                        "DeviceIndex": str(nic.get("Attachment", {}).get("DeviceIndex", 0)),
                    }
                    for nic in nics
                ]

            resources[logical_id] = {
                "Type": "AWS::EC2::Instance",
                "Properties": props,
            }


# ── EC2 Security Groups ───────────────────────────────────────────────────────
def convert_security_groups(data, resources):
    for sg in data.get("SecurityGroups", []):
        sgid = sg.get("GroupId", "unknown")
        logical_id = sanitize_id("EC2SecurityGroup", sgid)

        def map_rules(rules):
            out = []
            for r in rules:
                entry = {
                    "IpProtocol": str(r.get("IpProtocol", "-1")),
                }
                if r.get("FromPort") is not None:
                    entry["FromPort"] = r["FromPort"]
                if r.get("ToPort") is not None:
                    entry["ToPort"] = r["ToPort"]
                for ipv4 in r.get("IpRanges", []):
                    entry["CidrIp"] = ipv4.get("CidrIp", "")
                for ipv6 in r.get("Ipv6Ranges", []):
                    entry["CidrIpv6"] = ipv6.get("CidrIpv6", "")
                out.append(entry)
            return out

        props = {
            "GroupDescription": sg.get("Description", ""),
            "VpcId": sg.get("VpcId", ""),
            "SecurityGroupIngress": map_rules(sg.get("IpPermissions", [])),
            "SecurityGroupEgress": map_rules(sg.get("IpPermissionsEgress", [])),
        }
        resources[logical_id] = {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": props,
        }


# ── EC2 Volumes ───────────────────────────────────────────────────────────────
def convert_volumes(data, resources):
    for vol in data.get("Volumes", []):
        vid = vol.get("VolumeId", "unknown")
        logical_id = sanitize_id("EC2Volume", vid)
        props = {
            "Encrypted": vol.get("Encrypted", False),
            "VolumeType": vol.get("VolumeType", "gp2"),
            "AvailabilityZone": vol.get("AvailabilityZone", ""),
        }
        if vol.get("KmsKeyId"):
            props["KmsKeyId"] = vol["KmsKeyId"]
        resources[logical_id] = {
            "Type": "AWS::EC2::Volume",
            "Properties": props,
        }


# ── VPCs ──────────────────────────────────────────────────────────────────────
def convert_vpcs(data, resources):
    for vpc in data.get("Vpcs", []):
        vid = vpc.get("VpcId", "unknown")
        logical_id = sanitize_id("EC2VPC", vid)
        props = {
            "CidrBlock": vpc.get("CidrBlock", ""),
            "EnableDnsSupport": True,
            "EnableDnsHostnames": True,
        }
        resources[logical_id] = {
            "Type": "AWS::EC2::VPC",
            "Properties": props,
        }


# ── Subnets ───────────────────────────────────────────────────────────────────
def convert_subnets(data, resources):
    for subnet in data.get("Subnets", []):
        sid = subnet.get("SubnetId", "unknown")
        logical_id = sanitize_id("EC2Subnet", sid)
        props = {
            "VpcId": subnet.get("VpcId", ""),
            "CidrBlock": subnet.get("CidrBlock", ""),
            "MapPublicIpOnLaunch": subnet.get("MapPublicIpOnLaunch", False),
            "AvailabilityZone": subnet.get("AvailabilityZone", ""),
        }
        resources[logical_id] = {
            "Type": "AWS::EC2::Subnet",
            "Properties": props,
        }


# ── Network ACLs ──────────────────────────────────────────────────────────────
def convert_nacls(data, resources):
    for nacl in data.get("NetworkAcls", []):
        nid = nacl.get("NetworkAclId", "unknown")
        logical_id = sanitize_id("EC2NetworkAcl", nid)
        resources[logical_id] = {
            "Type": "AWS::EC2::NetworkAcl",
            "Properties": {
                "VpcId": nacl.get("VpcId", ""),
            },
        }
        # Each entry becomes a separate NetworkAclEntry resource
        for entry in nacl.get("Entries", []):
            rule_num = entry.get("RuleNumber", 0)
            direction = "Egress" if entry.get("Egress") else "Ingress"
            entry_logical = sanitize_id(
                f"EC2NetworkAclEntry{direction}",
                f"{nid}rule{rule_num}"
            )
            entry_props = {
                "NetworkAclId": nid,
                "RuleNumber": rule_num,
                "Protocol": str(entry.get("Protocol", "-1")),
                "RuleAction": entry.get("RuleAction", "deny"),
                "Egress": entry.get("Egress", False),
                "CidrBlock": entry.get("CidrBlock", ""),
            }
            if entry.get("PortRange"):
                entry_props["PortRange"] = {
                    "From": entry["PortRange"].get("From", 0),
                    "To": entry["PortRange"].get("To", 65535),
                }
            resources[entry_logical] = {
                "Type": "AWS::EC2::NetworkAclEntry",
                "Properties": entry_props,
            }


# ── IAM Roles ─────────────────────────────────────────────────────────────────
def convert_iam_roles(data, resources):
    for role in data.get("Roles", []):
        name = role.get("RoleName", "unknown")
        logical_id = sanitize_id("IAMRole", name)

        inline_policies = []
        for pname, pdoc in role.get("InlinePolicies", {}).items():
            inline_policies.append({
                "PolicyName": pname,
                "PolicyDocument": pdoc,
            })

        props = {
            "RoleName": name,
            "AssumeRolePolicyDocument": role.get("AssumeRolePolicyDocument", {}),
        }
        if inline_policies:
            props["Policies"] = inline_policies
        if role.get("ManagedPolicyArns"):
            props["ManagedPolicyArns"] = role["ManagedPolicyArns"]

        resources[logical_id] = {
            "Type": "AWS::IAM::Role",
            "Properties": props,
        }


# ── IAM Users ─────────────────────────────────────────────────────────────────
def convert_iam_users(data, resources):
    for user in data.get("Users", []):
        name = user.get("UserName", "unknown")
        logical_id = sanitize_id("IAMUser", name)

        inline_policies = []
        for pname, pdoc in user.get("InlinePolicies", {}).items():
            inline_policies.append({
                "PolicyName": pname,
                "PolicyDocument": pdoc,
            })

        props = {"UserName": name}
        if inline_policies:
            props["Policies"] = inline_policies
        if user.get("Groups"):
            props["Groups"] = user["Groups"]

        resources[logical_id] = {
            "Type": "AWS::IAM::User",
            "Properties": props,
        }


# ── IAM Policies ──────────────────────────────────────────────────────────────
def convert_iam_policies(data, resources):
    for policy in data.get("Policies", []):
        name = policy.get("PolicyName", "unknown")
        logical_id = sanitize_id("IAMPolicy", name)
        props = {
            "PolicyName": name,
            "PolicyDocument": policy.get("PolicyDocument", {}),
        }
        resources[logical_id] = {
            "Type": "AWS::IAM::ManagedPolicy",
            "Properties": props,
        }


# ── IAM Groups ────────────────────────────────────────────────────────────────
def convert_iam_groups(data, resources):
    for group in data.get("Groups", []):
        name = group.get("GroupName", "unknown")
        logical_id = sanitize_id("IAMGroup", name)
        resources[logical_id] = {
            "Type": "AWS::IAM::Group",
            "Properties": {"GroupName": name},
        }


# ── RDS Instances ─────────────────────────────────────────────────────────────
def convert_rds_instances(data, resources):
    for db in data.get("DBInstances", []):
        dbid = db.get("DBInstanceIdentifier", "unknown")
        logical_id = sanitize_id("RDSInstance", dbid)

        props = {
            "DBInstanceIdentifier": dbid,
            "DBInstanceClass":      db.get("DBInstanceClass", ""),
            "Engine":               db.get("Engine", ""),
            "EngineVersion":        db.get("EngineVersion", ""),
            "StorageEncrypted":     db.get("StorageEncrypted", False),
            "PubliclyAccessible":   db.get("PubliclyAccessible", True),
            "MultiAZ":              db.get("MultiAZ", False),
            "BackupRetentionPeriod": db.get("BackupRetentionPeriod", 0),
            "DeletionProtection":   db.get("DeletionProtection", False),
            "AutoMinorVersionUpgrade": db.get("AutoMinorVersionUpgrade", False),
            "CopyTagsToSnapshot":   db.get("CopyTagsToSnapshot", False),
            "EnableIAMDatabaseAuthentication": db.get("IAMDatabaseAuthenticationEnabled", False),
        }

        monitoring = db.get("MonitoringInterval", 0)
        if monitoring:
            props["MonitoringInterval"] = monitoring

        if db.get("PerformanceInsightsEnabled"):
            props["EnablePerformanceInsights"] = True

        resources[logical_id] = {
            "Type": "AWS::RDS::DBInstance",
            "Properties": props,
        }


# ── S3 Buckets ────────────────────────────────────────────────────────────────
def convert_s3_buckets(data, resources):
    for bucket in data.get("Buckets", []):
        name = bucket.get("Name", "unknown")
        logical_id = sanitize_id("S3Bucket", name)

        props = {"BucketName": name}

        # Encryption (CKV_AWS_19, CKV_AWS_145)
        sse = bucket.get("ServerSideEncryptionConfiguration")
        if sse:
            props["BucketEncryption"] = sse
        else:
            # Explicitly absent = not encrypted (Checkov will flag this)
            props["BucketEncryption"] = None

        # Versioning (CKV_AWS_21)
        ver = bucket.get("VersioningConfiguration", {})
        if ver.get("Status"):
            props["VersioningConfiguration"] = {"Status": ver["Status"]}

        # Logging (CKV_AWS_18)
        log = bucket.get("LoggingEnabled")
        if log:
            props["LoggingConfiguration"] = {
                "DestinationBucketName": log.get("TargetBucket", ""),
                "LogFilePrefix": log.get("TargetPrefix", ""),
            }

        # Public access block (CKV_AWS_53..56)
        pub = bucket.get("PublicAccessBlockConfiguration")
        if pub:
            props["PublicAccessBlockConfiguration"] = {
                "BlockPublicAcls": pub.get("BlockPublicAcls", False),
                "BlockPublicPolicy": pub.get("BlockPublicPolicy", False),
                "IgnorePublicAcls": pub.get("IgnorePublicAcls", False),
                "RestrictPublicBuckets": pub.get("RestrictPublicBuckets", False),
            }
        else:
            props["PublicAccessBlockConfiguration"] = {
                "BlockPublicAcls": False,
                "BlockPublicPolicy": False,
                "IgnorePublicAcls": False,
                "RestrictPublicBuckets": False,
            }

        resources[logical_id] = {
            "Type": "AWS::S3::Bucket",
            "Properties": props,
        }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    resources = {}

    converters = [
        ("ec2_instances.json",    convert_ec2_instances),
        ("ec2_security_groups.json", convert_security_groups),
        ("ec2_volumes.json",      convert_volumes),
        ("vpc_vpcs.json",         convert_vpcs),
        ("vpc_subnets.json",      convert_subnets),
        ("vpc_nacls.json",        convert_nacls),
        ("rds_instances.json",    convert_rds_instances),
        ("s3_buckets.json",       convert_s3_buckets),
    ]

    for filename, fn in converters:
        data = load(args.raw_dir, filename)
        before = len(resources)
        fn(data, resources)
        added = len(resources) - before
        print(f"[convert] {filename} → {added} resource(s)")

    if not resources:
        print("[WARN] No resources found — template will be empty.", file=sys.stderr)

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Auto-generated from live AWS account for security assessment",
        "Resources": resources,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(template, f, indent=2, default=str)

    print(f"[convert] Template written: {args.output} ({len(resources)} resources)")


if __name__ == "__main__":
    main()
