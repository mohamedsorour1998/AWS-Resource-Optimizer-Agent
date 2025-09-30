#!/usr/bin/env python3
"""
Create AgentCore Gateway with Semantic Search
Following AWS AgentCore Gateway documentation
"""
import boto3
import json
import sys

def create_gateway_with_semantic_search():
    """Create AgentCore Gateway with semantic search enabled"""

    # Load configuration
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found. Run 01-create-iam-role.py first")
        sys.exit(1)

    role_arn = config['aws']['gateway_role_arn']
    cognito_config = config.get('cognito', {})

    if not cognito_config:
        print("❌ Cognito configuration not found. Using existing Cognito setup")
        sys.exit(1)

    print(f"Creating AgentCore Gateway with Semantic Search")
    print(f"Using IAM role: {role_arn}")
    print(f"Using Cognito client: {cognito_config['client_id']}")

    # Initialize AgentCore client
    agentcore_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')

    gateway_name = 'resource-optimizer-gateway'

    # Gateway configuration with Cognito JWT and Semantic Search
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config['client_id']],
            "discoveryUrl": cognito_config['discovery_url']
        }
    }

    # SEMANTIC SEARCH configuration
    protocol_configuration = {
        "mcp": {
            "searchType": "SEMANTIC"
        }
    }

    try:
        print(f"\n🔧 Creating Gateway: {gateway_name}")
        print(f"  ✓ Semantic Search: ENABLED")
        print(f"  ✓ Debug Mode: ENABLED")

        gateway_response = agentcore_client.create_gateway(
            name=gateway_name,
            roleArn=role_arn,
            protocolType='MCP',
            authorizerType='CUSTOM_JWT',
            authorizerConfiguration=auth_config,
            protocolConfiguration=protocol_configuration,  # Semantic search
            exceptionLevel='DEBUG',  # Enable debug mode
            description='Resource Optimizer Gateway with semantic search for EC2, RDS, EBS, CloudWatch'
        )

        gateway_id = gateway_response["gatewayId"]
        gateway_url = gateway_response["gatewayUrl"]

        print(f"\n✅ Gateway created successfully!")
        print(f"  Gateway ID:  {gateway_id}")
        print(f"  Gateway URL: {gateway_url}")

        # Update configuration
        config['gateway'] = {
            'id': gateway_id,
            'url': gateway_url,
            'name': gateway_name
        }

        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f"\n✅ Configuration updated")

        return {
            'gateway_id': gateway_id,
            'gateway_url': gateway_url,
            'gateway_name': gateway_name
        }

    except Exception as e:
        print(f"❌ Error creating Gateway: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Creating AgentCore Gateway with Semantic Search")
    print("=" * 60)

    result = create_gateway_with_semantic_search()

    print("\n" + "=" * 60)
    print("✅ GATEWAY SETUP COMPLETE")
    print("=" * 60)
    print(f"Gateway Name: {result['gateway_name']}")
    print(f"Gateway ID:   {result['gateway_id']}")
    print(f"Gateway URL:  {result['gateway_url']}")
    print(f"Features:")
    print(f"  ✓ Semantic Search (intelligent tool discovery)")
    print(f"  ✓ Debug Mode (detailed error messages)")
    print("=" * 60)
    print("\n🎯 Next: Run 03-create-smithy-target.py")