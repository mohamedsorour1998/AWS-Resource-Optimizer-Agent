#!/usr/bin/env python3
"""
Create IAM Role for Resource Optimizer Gateway
Following AWS best practices for AgentCore Gateway
"""
import boto3
import json
import sys

def create_gateway_role():
    """Create IAM role for AgentCore Gateway with resource optimizer permissions"""

    iam_client = boto3.client('iam')
    role_name = 'ResourceOptimizerGatewayRole'

    # Trust policy - allows AgentCore Gateway to assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Permissions policy - what the gateway can do
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EC2ResourceAccess",
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeInstances",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeSnapshots",
                    "ec2:DescribeAddresses",
                    "ec2:DescribeImages",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeInstanceTypes",
                    "ec2:DescribeRegions"
                ],
                "Resource": "*"
            },
            {
                "Sid": "EBSResourceAccess",
                "Effect": "Allow",
                "Action": [
                    "ebs:ListSnapshotBlocks",
                    "ebs:ListChangedBlocks",
                    "ebs:GetSnapshotBlock"
                ],
                "Resource": "*"
            },
            {
                "Sid": "RDSResourceAccess",
                "Effect": "Allow",
                "Action": [
                    "rds:DescribeDBInstances",
                    "rds:DescribeDBSnapshots",
                    "rds:DescribeDBClusters",
                    "rds:ListTagsForResource"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchMetrics",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics",
                    "cloudwatch:GetMetricData"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents"
                ],
                "Resource": "*"
            },
            {
                "Sid": "S3SmithySpecAccess",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::cost-explorer-smithy-api",
                    "arn:aws:s3:::cost-explorer-smithy-api/*"
                ]
            }
        ]
    }

    print(f"Creating IAM role: {role_name}")

    try:
        # Create the role
        role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for CloudWatch Monitoring AgentCore Gateway - monitors AWS resources via CloudWatch, EBS, and Logs',
            MaxSessionDuration=3600
        )

        role_arn = role_response['Role']['Arn']
        print(f"✅ Role created: {role_arn}")

        # Attach inline policy
        print(f"Attaching permissions policy...")
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='ResourceOptimizerPermissions',
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✅ Permissions attached")

        # Update config.json
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"aws": {}}

        # Get account ID
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']

        config['aws'] = {
            'account_id': account_id,
            'gateway_role_arn': role_arn,
            'region': boto3.Session().region_name or 'us-east-1'
        }

        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Config updated")

        return {
            'role_name': role_name,
            'role_arn': role_arn,
            'account_id': account_id
        }

    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"⚠️  Role {role_name} already exists")
        role_arn = f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/{role_name}"

        # Update policy anyway
        print(f"Updating permissions policy...")
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='ResourceOptimizerPermissions',
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✅ Permissions updated")

        return {
            'role_name': role_name,
            'role_arn': role_arn
        }

    except Exception as e:
        print(f"❌ Error creating role: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Creating IAM Role for Resource Optimizer Gateway")
    print("=" * 60)

    result = create_gateway_role()

    print("\n" + "=" * 60)
    print("✅ IAM ROLE SETUP COMPLETE")
    print("=" * 60)
    print(f"Role Name: {result['role_name']}")
    print(f"Role ARN:  {result['role_arn']}")
    print("=" * 60)
    print("\n🎯 Next: Run 02-create-cognito-auth.py")