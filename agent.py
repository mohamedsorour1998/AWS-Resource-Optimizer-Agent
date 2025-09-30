#!/usr/bin/env python3
"""
AWS CloudWatch Monitoring Agent with AgentCore Gateway

Monitor AWS resources through natural language using:
- CloudWatch Metrics (EC2, RDS, Lambda, S3, EBS performance monitoring)
- CloudWatch Logs (Application and infrastructure log analysis)
- EBS (Volume and snapshot management)

Powered by Claude Sonnet 4.5, AgentCore Gateway with Semantic Search, and persistent memory.
"""
import json
import requests
import logging
import re
import time
from pathlib import Path
from datetime import datetime

# Check if config exists
if not Path('config.json').exists():
    print("❌ config.json not found. Please run setup scripts first")
    exit(1)

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent
from bedrock_agentcore.memory import MemoryClient

# Setup logging - only show errors
logging.basicConfig(
    level=logging.ERROR,
    format='%(levelname)s: %(message)s'
)
# Suppress all library warnings
logging.getLogger("strands").setLevel(logging.ERROR)
logging.getLogger("client").setLevel(logging.ERROR)
logging.getLogger("mcp").setLevel(logging.ERROR)
logging.getLogger("bedrock_agentcore").setLevel(logging.ERROR)

logger = logging.getLogger("cloudwatch-agent")
logger.setLevel(logging.ERROR)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

CLIENT_ID = config['cognito']['client_id']
CLIENT_SECRET = config['cognito']['client_secret']
TOKEN_URL = config['cognito']['token_url']
GATEWAY_URL = config['gateway']['url']
REGION = config['aws'].get('region', 'us-east-1')
ACTOR_ID = "resource-optimizer-001"  # Unique identifier for this agent
SESSION_ID = f"main-session-{ACTOR_ID}"  # Fixed session ID for memory continuity

def fetch_access_token(client_id, client_secret, token_url):
    """Get Cognito access token (following docs pattern)"""
    response = requests.post(
        token_url,
        data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json()['access_token']

def create_streamable_http_transport(mcp_url: str, access_token: str):
    """Create streamable HTTP transport (following docs pattern)"""
    return streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {access_token}"})

def get_full_tools_list(client):
    """List tools w/ support for pagination (following docs pattern)"""
    more_tools = True
    tools = []
    pagination_token = None
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            more_tools = True
            pagination_token = tmp_tools.pagination_token
    return tools

class CostMemoryHookProvider(HookProvider):
    """Memory hook for cost optimization agent - stores and retrieves conversation history"""

    def __init__(self, memory_client: MemoryClient, memory_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id

    def on_agent_initialized(self, event: AgentInitializedEvent):
        """Load recent conversation history when agent starts"""
        try:
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")

            if not actor_id or not session_id:
                logger.warning("Missing actor_id or session_id in agent state")
                return

            # Load the last 5 conversation turns from memory
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=5
            )

            if recent_turns:
                # Format conversation history for context
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message['role']
                        content = message['content']['text']
                        context_messages.append(f"{role}: {content}")

                context = "\n".join(context_messages)
                # Add context to agent's system prompt
                event.agent.system_prompt += f"\n\nRecent conversation:\n{context}"
                logger.debug(f"✅ Loaded {len(recent_turns)} conversation turns from memory")

        except Exception as e:
            logger.error(f"Memory load error: {e}")

    def on_message_added(self, event: MessageAddedEvent):
        """Store messages in memory"""
        messages = event.agent.messages
        try:
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")

            if messages[-1]["content"][0].get("text"):
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=actor_id,
                    session_id=session_id,
                    messages=[(messages[-1]["content"][0]["text"], messages[-1]["role"])]
                )
                logger.debug("✅ Message saved to memory")
        except Exception as e:
            logger.error(f"Memory save error: {e}")

    def register_hooks(self, registry: HookRegistry):
        """Register memory hooks"""
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)

def create_or_get_memory():
    """Create or retrieve AgentCore Memory for resource optimization"""
    memory_client = MemoryClient(region_name=REGION)
    memory_name = "ResourceOptimizerMemory"

    try:
        # Try to find existing memory
        memories = memory_client.list_memories()
        existing_memory = next((m for m in memories if m['id'].startswith(memory_name)), None)

        if existing_memory:
            memory_id = existing_memory['id']
            logger.debug(f"✅ Using existing memory: {memory_id}")
            return memory_client, memory_id

        # Create new memory resource for short-term memory
        logger.debug(f"📝 Creating new memory: {memory_name}")
        memory = memory_client.create_memory_and_wait(
            name=memory_name,
            strategies=[],  # No strategies for short-term memory
            description="Short-term memory for AWS cost optimization conversations",
            event_expiry_days=30,  # Keep conversation history for 30 days
        )
        memory_id = memory['id']
        logger.debug(f"✅ Created memory: {memory_id}")

        # Save memory ID to config
        config['memory'] = {'id': memory_id, 'name': memory_name}
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)

        return memory_client, memory_id

    except Exception as e:
        logger.error(f"❌ Memory error: {e}")
        raise

def create_resource_optimizer_agent():
    """Create agent with MCP tools (following docs pattern)"""
    print("\n" + "=" * 60)
    print("🔧  AWS Resource Optimizer Agent")
    print("=" * 60)

    # Authenticate with Cognito
    print("🔐 Authenticating with gateway...")
    access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    print("✅ Authentication successful")

    # Connect to AgentCore Gateway
    print("📡 Connecting to AgentCore Gateway...")
    mcp_client = MCPClient(lambda: create_streamable_http_transport(GATEWAY_URL, access_token))

    with mcp_client:
        # List available tools
        all_tools = get_full_tools_list(mcp_client)

        # Filter tools with names <= 64 characters (Bedrock limitation)
        tools = [tool for tool in all_tools if len(tool.tool_name) <= 64]

        print(f"✅ Gateway connected ({len(tools)} tools available)")

        # Setup AgentCore Memory
        print("🧠 Loading AgentCore Memory...")
        memory_client, memory_id = create_or_get_memory()
        print(f"✅ Memory ready (ID: {memory_id})")

        # Create Bedrock model with streaming disabled
        bedrock_model = BedrockModel(
            model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name="us-east-1",
            temperature=0.3,
            streaming=False
        )

        # Create agent with MCP tools AND memory hooks (docs pattern)
        agent = Agent(
            name="ResourceOptimizerAgent",
            system_prompt=f"""You are an AWS Resource Optimizer powered by Claude Sonnet 4.5 with persistent memory.

WHAT YOU DO:
Optimize and monitor AWS resources using three API targets:

1. CloudWatch Metrics API:
   - Monitor performance across ALL AWS services (EC2, RDS, Lambda, S3, EBS, etc.)
   - Get metric statistics: CPU, memory, disk, network, invocations, errors
   - List available metrics and analyze trends
   - Identify underutilized or overutilized resources

2. CloudWatch Logs API:
   - Search and analyze log groups across services
   - Filter log events for errors and patterns
   - Analyze Lambda function logs, application logs, infrastructure logs
   - Troubleshoot issues using log data

3. EBS API:
   - Manage EBS volumes and snapshots
   - List snapshot blocks
   - Optimize storage resources

WHAT YOU DON'T HAVE:
- NO direct EC2 API (use CloudWatch Metrics to monitor EC2 instances)
- NO direct RDS API (use CloudWatch Metrics to monitor RDS databases)
- NO direct Lambda API (use CloudWatch Metrics + Logs for Lambda monitoring)

YOUR GOAL:
Help users optimize AWS resource usage by:
- Identifying idle or underutilized resources
- Analyzing performance bottlenecks
- Recommending cost optimizations
- Troubleshooting issues via logs and metrics

COMMUNICATION STYLE:
- Be conversational and helpful
- Use plain text only (NO markdown formatting like ** or __)
- Provide specific values, thresholds, and actionable recommendations
- Explain technical concepts in simple terms
- Remember previous conversations and reference them when relevant

IMPORTANT RULES:
- ONLY call tools when users ask about metrics, logs, resources, or optimization
- DO NOT call tools for greetings, names, or casual conversation
- Answer memory questions WITHOUT calling any tools
- Be honest about API limitations
- Focus on optimization and actionable insights

Today's date: {datetime.now().strftime('%Y-%m-%d')}
""",
            model=bedrock_model,
            tools=tools,  # Pass ALL compatible MCP tools directly to the agent
            hooks=[CostMemoryHookProvider(memory_client, memory_id)],  # Add memory hooks
            state={"actor_id": ACTOR_ID, "session_id": SESSION_ID},  # Required for memory
            callback_handler=None  # Disable console output to prevent duplicates
        )

        return agent, mcp_client, memory_client, memory_id

def main():
    """Main entry point"""
    try:
        # Create agent with MCP tools and memory
        agent, mcp_client, memory_client, memory_id = create_resource_optimizer_agent()

        print("=" * 60)
        print("Welcome! I'm your AWS Resource Optimizer powered by")
        print("Claude Sonnet 4.5 with AgentCore Gateway & Semantic Search")
        print("\n" + "-" * 60)
        print("I optimize AWS resources using:")
        print("  📊 CloudWatch Metrics (Performance monitoring)")
        print("  📝 CloudWatch Logs (Log analysis)")
        print("  💾 EBS API (Volume & snapshot management)")
        print("\n" + "-" * 60)
        print("Try asking:")
        print("  • List available metrics for my resources")
        print("  • Show me underutilized resources")
        print("  • Analyze Lambda function performance")
        print("  • Search logs for errors")
        print("  • What did we discuss last time?")
        print("-" * 60)
        print("Type 'exit' to quit")
        print("=" * 60)

        # CRITICAL: Agent must be used within MCP client context manager (docs requirement)
        with mcp_client:
            # Interactive loop
            while True:
                try:
                    user_input = input("\n👤 You: ")
                    if user_input.lower() == "exit":
                        print("\nGoodbye! Keep monitoring those AWS resources! 👋")
                        break

                    if not user_input.strip():
                        continue

                    # Call the agent - it will automatically use MCP tools as needed
                    response = agent(user_input)

                    # Remove thinking tags from response
                    if isinstance(response, str):
                        # Remove all <thinking>...</thinking> blocks (can appear multiple times)
                        cleaned_response = re.sub(r'<thinking>.*?</thinking>\s*', '', response, flags=re.DOTALL | re.IGNORECASE)
                        # Also remove any remaining thinking patterns
                        cleaned_response = re.sub(r'\s*<thinking>.*', '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
                        cleaned_response = cleaned_response.strip()

                        # Check if it's a rate limit error and provide helpful message
                        if 'rate limit' in cleaned_response.lower() or 'throttl' in cleaned_response.lower():
                            print(f"\n⚠️  AWS API rate limit reached.")
                            print("💡 Wait a moment and try again, or ask about different resources.")
                        elif cleaned_response:
                            print(f"\n🤖 Agent: {cleaned_response}")
                    else:
                        print(f"\n🤖 Agent: {response}")

                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break
                except EOFError:
                    print("\n\nInput stream ended.")
                    break
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    if "rate limit" in str(e).lower():
                        print("💡 Try again in a few minutes - AWS has strict rate limits")
                    print("Please try a different question.")

    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")

if __name__ == "__main__":
    main()