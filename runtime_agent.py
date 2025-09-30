#!/usr/bin/env python3
"""
AWS Resource Optimizer Agent - AgentCore Runtime Edition

Deployable to Amazon Bedrock AgentCore Runtime.
Monitors AWS resources via CloudWatch Metrics, CloudWatch Logs, and EBS APIs.
"""
import json
import os
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import requests

# Initialize AgentCore App
app = BedrockAgentCoreApp()

# Configuration from environment variables
GATEWAY_URL = os.environ.get('GATEWAY_URL')
COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID')
COGNITO_CLIENT_SECRET = os.environ.get('COGNITO_CLIENT_SECRET')
COGNITO_TOKEN_URL = os.environ.get('COGNITO_TOKEN_URL')

def get_access_token():
    """Get Cognito OAuth token for gateway access"""
    response = requests.post(
        COGNITO_TOKEN_URL,
        data=f"grant_type=client_credentials&client_id={COGNITO_CLIENT_ID}&client_secret={COGNITO_CLIENT_SECRET}",
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json()['access_token']

def create_transport():
    """Create MCP transport"""
    token = get_access_token()
    return streamablehttp_client(GATEWAY_URL, headers={"Authorization": f"Bearer {token}"})

def get_tools():
    """Load tools from gateway"""
    mcp_client = MCPClient(create_transport)
    with mcp_client:
        all_tools = []
        pagination_token = None
        while True:
            result = mcp_client.list_tools_sync(pagination_token=pagination_token)
            all_tools.extend(result)
            if result.pagination_token is None:
                break
            pagination_token = result.pagination_token

        # Filter tools (Bedrock limitation: <= 64 chars)
        tools = [t for t in all_tools if len(t.tool_name) <= 64]
        return tools, mcp_client

# Initialize agent with tools
tools, mcp_client = get_tools()

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    temperature=0.3
)

agent = Agent(
    name="ResourceOptimizerAgent",
    system_prompt="""You are an AWS Resource Optimizer powered by Claude Sonnet 4.5.

WHAT YOU DO:
- Monitor AWS resources via CloudWatch Metrics (EC2, RDS, Lambda, S3, EBS)
- Analyze logs via CloudWatch Logs
- Manage storage via EBS API

YOUR GOAL:
Help users optimize AWS resource usage by identifying idle resources, analyzing performance, and recommending optimizations.

RULES:
- Use plain text (no markdown)
- Be concise and actionable
- Call tools ONLY when asked about metrics, logs, or resources
- Focus on optimization insights
""",
    model=model,
    tools=tools
)

@app.entrypoint
def invoke(payload):
    """AgentCore Runtime entrypoint"""
    user_message = payload.get("prompt", "Hello! How can I help optimize your AWS resources?")

    # Invoke agent
    with mcp_client:
        result = agent(user_message)

    return {
        "result": result.message if hasattr(result, 'message') else str(result)
    }

if __name__ == "__main__":
    # For local testing
    app.run()