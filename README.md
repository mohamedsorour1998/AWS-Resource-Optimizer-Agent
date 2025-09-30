# AWS Resource Optimizer Agent 
[GitHub] (https://github.com/mohamedsorour1998/AWS-Resource-Optimizer-Agent)

I built a production-ready **AWS Resource Optimizer Agent** with **Amazon Bedrock AgentCore Gateway**, **Claude Sonnet 4.5**, and the **Strands Agents SDK**, and it completely transformed how I manage my cloud environment. Instead of digging through CloudWatch dashboards or juggling CLI commands, I can now just ask questions like *“Which EC2 instances are underutilized?”* or *“Show me Lambda errors from the last 24 hours”*—and the agent instantly pulls the right metrics, logs, or EBS data from over **137 AWS tools**. I can run it locally for testing or deploy it to **AgentCore Runtime** for secure, scalable use, with built-in **OAuth, memory, and semantic search** that make it simple and powerful. Setup took only a few steps—create an IAM role, load the Smithy specs for CloudWatch, Logs, and EBS, and the agent was live. It saves me hours of manual work and gives me confidence my infrastructure is running efficiently—I can’t imagine going back.


![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/rc880c782kpiwgn6wpdu.png)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Deployment Options](#deployment-options)
  - [Option 1: Local Development](#option-1-local-development-cli)
  - [Option 2: AgentCore Runtime](#option-2-agentcore-runtime-production)
- [API Targets & Capabilities](#api-targets--capabilities)
- [Setup Guide](#setup-guide)
- [Configuration Reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## Overview

### What It Does

AI-powered agent that monitors and optimizes AWS resources through natural language conversations using:

- **CloudWatch Metrics API**: Monitor EC2, RDS, Lambda, S3, EBS performance
- **CloudWatch Logs API**: Analyze application and infrastructure logs
- **EBS API**: Manage volumes and snapshots

### Key Features

- ✅ **137 AWS Tools Access**:  in AgentCore GatewayCloudWatch, Logs, and EBS APIs via AgentCore Gateway
![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/6ews3vw0stnzvodpkhlw.png)
- ✅ **Semantic Search**: Intelligent tool discovery via AgentCore Gateway
![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/fb7yc3uy6y46201mbder.png)
- ✅ **Persistent Memory**: Cross-session conversation continuity
![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/6lrhg7y3h18dyt7h9zcj.png)
- ✅ **Ready**: Ready local CLI and in progress to be Deployable to AgentCore Runtime
![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/o1bghpfjwuec9478eo4g.png)
- ✅ **OAuth Secured**: Cognito-based authentication
![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/pvgxy5sta61pt75pmaqi.png)


### Use Cases

- Identify idle or underutilized resources
- Analyze Lambda function errors
- Monitor RDS database performance
- Search CloudWatch logs for issues
- Optimize EBS storage usage

![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/66p6l2uaoa0ndefxajqz.png)

---

## Architecture

![Image description](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/8xmvuxrdbjhv5w07mtzn.png)

### Components

1. **AgentCore Gateway**: MCP protocol server exposing AWS APIs as tools
2. **Claude Sonnet 4.5**: LLM for natural language understanding
3. **Strands Agents**: Agent orchestration framework
4. **AgentCore Memory**: Persistent conversation storage
5. **Cognito**: OAuth 2.0 authentication

---

## Deployment Options

### Option 1: Local Development (CLI)

**Best for**: Development, testing, rapid iteration

#### Prerequisites

- Python 3.10+
- AWS credentials configured
- Smithy API specs in S3 (`cost-explorer-smithy-api` bucket)
- IAM permissions for bedrock-agentcore, IAM, Cognito

#### Setup Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create infrastructure
cd setup
python3 01-create-iam-role.py
python3 02-create-gateway.py
python3 03-create-smithy-targets.py

# Wait 60 seconds for tools to sync

# 3. Run agent locally
cd ..
python3 agent.py
```

**Usage**:
```bash
python3 agent.py
👤 You: List my CloudWatch metrics
🤖 Agent: [Shows available metrics...]
```

---

### Option 2: AgentCore Runtime (Production)

**Best for**: Production deployment, managed hosting, team environments

#### Prerequisites

- AWS Account with bedrock-agentcore permissions
- Python 3.10+
- Boto3 installed
- Model access: Anthropic Claude Sonnet 4.5 enabled in Bedrock console
- Infrastructure from Option 1 setup (Gateway, Targets, IAM Role)

#### Deployment Steps

**1. Configure environment variables**:

```bash
# Copy template
cp .env.template .env

# Edit .env with your values from config.json
GATEWAY_URL=https://resource-optimizer-gateway-xxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
COGNITO_CLIENT_ID=your_client_id
COGNITO_CLIENT_SECRET=your_secret
COGNITO_TOKEN_URL=https://your-domain.auth.us-east-1.amazoncognito.com/oauth2/token
```

**2. Deploy to AgentCore Runtime**:

```bash
# Option A: Use deploy script
./deploy.sh

# Option B: Manual deployment
pip install bedrock-agentcore-starter-toolkit
agentcore configure -e runtime_agent.py
agentcore launch
```

**3. Test deployment**:

```bash
# Quick test
agentcore invoke '{"prompt": "List my Lambda functions"}'

# Get agent ARN (from output or bedrock_agentcore.yaml)
```

**4. Invoke from application**:

```python
import json
import boto3

client = boto3.client('bedrock-agentcore')

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:agent/AGENT_ID',
    payload=json.dumps({"prompt": "Show me idle EC2 instances"}).encode()
)

# Process streaming response
for chunk in response.get("response", []):
    print(chunk.decode('utf-8'))
```

#### Runtime Management

**View logs**:
```bash
# Check CloudWatch Logs (location shown in deploy output)
aws logs tail /aws/bedrock-agentcore/agent/YOUR_AGENT_ID --follow
```

**Update agent**:
```bash
# Make code changes, then redeploy
agentcore launch
```

**Delete runtime**:
```bash
# Via CLI
aws bedrock-agentcore delete-agent-runtime --agent-runtime-arn YOUR_ARN

# Or use AWS Console
```

---

## API Targets & Capabilities

### CloudWatch Metrics (40 tools)

**Purpose**: Monitor AWS resource performance

**Key Operations**:
- `ListMetrics`: Discover available metrics
- `GetMetricStatistics`: Retrieve metric data points
- `GetMetricData`: Query multiple metrics

**Example Queries**:
- "Show me EC2 CPU utilization"
- "List Lambda invocation metrics"
- "Get RDS database read latency"

### CloudWatch Logs (91 tools)

**Purpose**: Search and analyze logs

**Key Operations**:
- `DescribeLogGroups`: List log groups
- `FilterLogEvents`: Search logs with patterns
- `GetLogEvents`: Retrieve log entries

**Example Queries**:
- "Search Lambda logs for errors"
- "Show recent log events for my application"
- "Find API Gateway 5xx errors"

### EBS (6 tools)

**Purpose**: Manage EBS volumes and snapshots

**Key Operations**:
- `ListSnapshotBlocks`: List snapshot blocks
- `GetSnapshotBlock`: Retrieve block data

**Example Queries**:
- "List my EBS volumes"
- "Show snapshot details"

---

## Setup Guide

### 1. Create IAM Role

**Script**: `setup/01-create-iam-role.py`

**What it creates**:
- Role name: `ResourceOptimizerGatewayRole`
- Trust policy: Allows bedrock-agentcore.amazonaws.com
- Permissions: CloudWatch, Logs, EBS, S3 access

**Permissions granted**:
```json
{
  "CloudWatch": ["GetMetricStatistics", "ListMetrics", "GetMetricData"],
  "Logs": ["DescribeLogGroups", "FilterLogEvents", "GetLogEvents"],
  "EBS": ["ListSnapshotBlocks", "GetSnapshotBlock"],
  "S3": ["GetObject", "ListBucket"] // For Smithy specs
}
```

**Run**:
```bash
python3 setup/01-create-iam-role.py
```

### 2. Create AgentCore Gateway

**Script**: `setup/02-create-gateway.py`

**What it creates**:
- Gateway with MCP protocol
- **Semantic Search enabled** (intelligent tool selection)
- Debug mode for detailed errors
- Cognito OAuth authentication

**Features**:
```python
protocolConfiguration = {
    "mcp": {"searchType": "SEMANTIC"}  // Critical for 137 tools
}
```

**Run**:
```bash
python3 setup/02-create-gateway.py
```

**Output**: Gateway URL stored in `config.json`

### 3. Create Smithy Targets

**Script**: `setup/03-create-smithy-targets.py`

**What it creates**:
- **CloudWatchTarget** (371KB Smithy spec)
- **CloudWatchLogsTarget** (645KB Smithy spec)
- **EBSTarget** (92KB Smithy spec)

**Smithy Specs Required**:
Upload to S3 bucket `cost-explorer-smithy-api`:
- `cloudwatch-2010-08-01.json`
- `cloudwatch-logs-2014-03-28.json`
- `ebs-2019-11-02.json`

**Run**:
```bash
python3 setup/03-create-smithy-targets.py
# Wait 60 seconds for tools to sync
```

**Output**: Target IDs stored in `config.json`

---

## Configuration Reference

### config.json Structure

```json
{
  "aws": {
    "account_id": "339712964409",
    "gateway_role_arn": "arn:aws:iam::ACCOUNT:role/ResourceOptimizerGatewayRole",
    "region": "us-east-1"
  },
  "cognito": {
    "user_pool_id": "us-east-1_xxx",
    "client_id": "xxx",
    "client_secret": "xxx",
    "discovery_url": "https://cognito-idp.us-east-1.amazonaws.com/...",
    "token_url": "https://your-domain.auth.us-east-1.amazoncognito.com/oauth2/token"
  },
  "gateway": {
    "id": "resource-optimizer-gateway-xxx",
    "url": "https://resource-optimizer-gateway-xxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
    "name": "resource-optimizer-gateway"
  },
  "smithy_targets": [
    {
      "id": "XXXXX",
      "name": "CloudWatchTarget",
      "uri": "s3://cost-explorer-smithy-api/cloudwatch-2010-08-01.json"
    },
    {
      "id": "XXXXX",
      "name": "CloudWatchLogsTarget",
      "uri": "s3://cost-explorer-smithy-api/cloudwatch-logs-2014-03-28.json"
    },
    {
      "id": "XXXXX",
      "name": "EBSTarget",
      "uri": "s3://cost-explorer-smithy-api/ebs-2019-11-02.json"
    }
  ],
  "memory": {
    "id": "ResourceOptimizerMemory-xxx",
    "name": "ResourceOptimizerMemory"
  }
}
```

### Environment Variables (AgentCore Runtime)

```bash
# Required
GATEWAY_URL=https://your-gateway.gateway.bedrock-agentcore.REGION.amazonaws.com/mcp
COGNITO_CLIENT_ID=your_client_id
COGNITO_CLIENT_SECRET=your_client_secret
COGNITO_TOKEN_URL=https://your-domain.auth.REGION.amazoncognito.com/oauth2/token

# Optional
AWS_REGION=us-east-1  # Defaults to us-east-1
```

---

## Troubleshooting

### Local Development Issues

#### Agent shows 0 tools
**Cause**: Targets not synced yet
**Fix**: Wait 60 seconds after running `03-create-smithy-targets.py`

#### Permission denied errors
**Cause**: Missing IAM permissions
**Fix**:
```bash
# Add AgentCore permissions to your IAM user
aws iam put-user-policy --user-name YOUR_USER \
  --policy-name AgentCoreAdmin \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "bedrock-agentcore:*",
      "Resource": "*"
    }]
  }'
```

#### Smithy spec too large error
**Cause**: Spec exceeds 2MB limit
**Fix**: We use specs under 2MB (CloudWatch 371KB, Logs 645KB, EBS 92KB)

### AgentCore Runtime Issues

#### CodeBuild build error
**Check**:
1. View CodeBuild logs in AWS Console
2. Verify IAM permissions include CodeBuild access
3. Check requirements.txt is valid

#### Model access denied
**Fix**:
1. Enable Anthropic Claude Sonnet 4.5 in Bedrock console
2. Verify region matches (default: us-west-2 for runtime, us-east-1 for gateway)

#### Docker not found warning
**Info**: Can be ignored - CodeBuild doesn't need Docker unless using `--local` flag

### Gateway Issues

#### list_gateway_targets returns 0 targets
**Note**: This API has known issues. Use `get_gateway_target(targetId=X)` instead

#### Tools not loading after target creation
**Fix**:
1. Wait 60 seconds for synchronization
2. Verify S3 bucket contains Smithy specs: `aws s3 ls s3://cost-explorer-smithy-api/`

---

## Project Structure

```
aws-cost-optimization-agent/
├── agent.py                    # Local CLI agent
├── runtime_agent.py            # AgentCore Runtime agent
├── requirements.txt            # Python dependencies
├── config.json                 # Auto-generated configuration
├── .env.template               # Environment template
├── deploy.sh                   # Runtime deployment script
├── README.md                   # This file
├── COMPLETION-SUMMARY.md       # Project history
└── setup/
    ├── 01-create-iam-role.py       # IAM role creation
    ├── 02-create-gateway.py        # Gateway with semantic search
    └── 03-create-smithy-targets.py # All 3 API targets
```

### Key Files

- **agent.py**: Interactive CLI agent for local development
- **runtime_agent.py**: Deployable agent for AgentCore Runtime
- **config.json**: Auto-generated by setup scripts (not in git)
- **.env**: Environment variables for runtime (not in git)

---

## Technical Specifications

### Performance

- **Startup**: ~3 seconds (local), ~1 second (runtime)
- **Tool Loading**: 137 tools (40 CloudWatch + 91 Logs + 6 EBS)
- **Response Time**: 2-4 seconds for typical queries
- **Memory**: Last 5 conversation turns (local), stateless (runtime)

### Limits

- **Smithy Spec Size**: 2MB maximum per target
- **Tool Name Length**: 64 characters (Bedrock limitation)
- **Context Window**: 200K tokens (Claude Sonnet 4.5)
- **Rate Limits**: CloudWatch 400+ req/sec (high)

### Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| LLM | Claude Sonnet 4.5 | 20250929 |
| Agent Framework | Strands Agents | Latest |
| Gateway | AgentCore Gateway | MCP Protocol |
| Memory | AgentCore Memory | Short-term (30 days) |
| Auth | Amazon Cognito | OAuth 2.0 |
| Runtime | AgentCore Runtime | Container-based |

---

## Security

### Authentication Flow

1. Agent requests OAuth token from Cognito
2. Token passed in Authorization header to Gateway
3. Gateway assumes IAM role for AWS API calls
4. All communication over TLS

### Best Practices

- ✅ Use least-privilege IAM policies
- ✅ Rotate Cognito client secrets regularly
- ✅ Enable CloudWatch logging for audit trail
- ✅ Use VPC endpoints for private access (optional)
- ✅ Review IAM role permissions quarterly

---

## Resources

- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Runtime Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/userguide/runtime.html)
- [Strands Agents SDK](https://strandsagents.com/)
- [Model Context Protocol](https://modelcontextprotocol.org/)
- [AWS CloudWatch](https://aws.amazon.com/cloudwatch/)

---

## Support

For issues:
1. Check troubleshooting section above
2. Review CloudWatch Logs
3. Verify configuration in `config.json`
4. Check AWS service quotas

---

**Status**: ✅ Production Not Ready yet (Still facing some issues in runtime, once i solve it i will update the code and the post)
**Last Updated**: September 30, 2025
**Total Tools**: 137 across 3 API targets