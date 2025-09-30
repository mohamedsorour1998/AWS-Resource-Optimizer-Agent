#!/bin/bash
# Deploy AWS Resource Optimizer Agent to AgentCore Runtime

set -e

echo "=========================================="
echo "AWS Resource Optimizer - AgentCore Deploy"
echo "=========================================="

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "❌ pip not found"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found"
    exit 1
fi

echo "✅ Prerequisites checked"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit strands-agents

echo "✅ Dependencies installed"

# Configure agent
echo ""
echo "Configuring AgentCore deployment..."
agentcore configure -e runtime_agent.py

# Deploy
echo ""
echo "Deploying to AgentCore Runtime..."
echo "(This may take 5-10 minutes)"
agentcore launch

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Note the Agent ARN from output above"
echo "2. Test with: agentcore invoke '{\"prompt\": \"hello\"}'"
echo "3. Invoke from SDK using the Agent ARN"
echo ""