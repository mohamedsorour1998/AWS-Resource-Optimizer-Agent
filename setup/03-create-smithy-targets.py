#!/usr/bin/env python3
"""
Create All Smithy Targets for Resource Optimizer
Creates CloudWatch, CloudWatch Logs, and EBS targets
"""
import boto3
import json
import sys
import time

def create_all_smithy_targets():
    """Create all Smithy targets in one go"""

    # Load configuration
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found. Run previous setup scripts first")
        sys.exit(1)

    gateway_id = config['gateway']['id']
    s3_bucket = 'cost-explorer-smithy-api'

    print(f"Creating Smithy Targets for Gateway: {gateway_id}")
    print(f"Using S3 bucket: {s3_bucket}")

    client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')

    # Credential configuration - use Gateway's IAM role
    credential_config = {
        "credentialProviderType": "GATEWAY_IAM_ROLE"
    }

    # Define all targets to create
    targets_to_create = [
        {
            'name': 'CloudWatchTarget',
            'uri': f's3://{s3_bucket}/cloudwatch-2010-08-01.json',
            'description': 'CloudWatch Metrics for monitoring all AWS resources',
            'size': '371KB'
        },
        {
            'name': 'CloudWatchLogsTarget',
            'uri': f's3://{s3_bucket}/cloudwatch-logs-2014-03-28.json',
            'description': 'CloudWatch Logs for log analysis and monitoring',
            'size': '645KB'
        },
        {
            'name': 'EBSTarget',
            'uri': f's3://{s3_bucket}/ebs-2019-11-02.json',
            'description': 'EBS for volume and snapshot management',
            'size': '91KB'
        }
    ]

    created_targets = []

    print("\n" + "=" * 60)
    print("Creating Targets")
    print("=" * 60)

    for target_spec in targets_to_create:
        smithy_config = {
            "mcp": {
                "smithyModel": {
                    "s3": {
                        "uri": target_spec['uri']
                    }
                }
            }
        }

        try:
            print(f"\n🔧 Creating: {target_spec['name']} ({target_spec['size']})")
            print(f"   URI: {target_spec['uri']}")

            response = client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=target_spec['name'],
                description=target_spec['description'],
                targetConfiguration=smithy_config,
                credentialProviderConfigurations=[credential_config]
            )

            target_id = response['targetId']
            print(f"   ✅ Created: {target_id}")

            created_targets.append({
                'id': target_id,
                'name': target_spec['name'],
                'uri': target_spec['uri'],
                'description': target_spec['description']
            })

            # Small delay between target creations
            time.sleep(2)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    if created_targets:
        # Update configuration
        config['smithy_targets'] = created_targets

        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f"\n✅ Configuration updated with {len(created_targets)} targets")

    return created_targets

if __name__ == "__main__":
    print("=" * 60)
    print("Creating All Smithy Targets")
    print("=" * 60)

    results = create_all_smithy_targets()

    if results:
        print("\n" + "=" * 60)
        print("✅ SMITHY TARGETS SETUP COMPLETE")
        print("=" * 60)
        print(f"Created {len(results)} targets:")
        for target in results:
            print(f"  • {target['name']}: {target['id']}")
        print("\nServices Available:")
        print("  ✓ CloudWatch (Metrics for EC2, RDS, Lambda, etc.)")
        print("  ✓ CloudWatch Logs (Log Analysis)")
        print("  ✓ EBS (Volume Management)")
        print("=" * 60)
        print("\n⏰ Wait 60 seconds for tools to sync, then run:")
        print("   python3 agent.py")
    else:
        print("\n❌ No targets were created")
        sys.exit(1)