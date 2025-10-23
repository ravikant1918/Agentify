import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv

load_dotenv()

# Try to import LangChain dependencies
try:
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain.tools import BaseTool
    from langchain.memory import ConversationBufferWindowMemory
    from langchain_openai import AzureChatOpenAI, ChatOpenAI
    from langchain.prompts import PromptTemplate
    from langchain import hub
    from pydantic import Field
    LANGCHAIN_AVAILABLE = True
    print("[INFO] LangChain is available")
except ImportError:
    print("[WARN] LangChain not installed. Install with: pip install langchain langchain-openai langchainhub")
    LANGCHAIN_AVAILABLE = False
    # Create placeholder classes
    class BaseTool:
        def __init__(self, **kwargs):
            pass
    class Field:
        def __init__(self, **kwargs):
            pass


if LANGCHAIN_AVAILABLE:
    class MCPTool(BaseTool):
        """LangChain tool wrapper for MCP tools"""
        
        name: str = Field(description="The name of the tool")
        description: str = Field(description="The description of the tool")
        session: ClientSession = Field(description="The MCP session", exclude=True)
        tool_schema: Dict[str, Any] = Field(description="The tool schema", exclude=True)
        
        def __init__(self, name: str, description: str, session: ClientSession, schema: Dict[str, Any], **kwargs):
            super().__init__(
                name=name,
                description=description,
                session=session,
                tool_schema=schema,
                **kwargs
            )
        
        async def _arun(self, *args, **kwargs) -> str:
            """Async implementation of the tool"""
            try:
                # Handle LangChain input format
                if len(args) == 1 and isinstance(args[0], str):
                    # Check if it's a JSON string first
                    try:
                        tool_args = json.loads(args[0])
                        print(f"[DEBUG] Parsed LangChain JSON input: {tool_args}")
                    except json.JSONDecodeError:
                        # If it's not JSON, it might be a direct string argument for specific tools
                        if self.name == "get_entity":
                            # For get_entity, the string should be treated as the URN
                            tool_args = {"urn": args[0]}
                        else:
                            # For other tools, treat as query
                            tool_args = {"query": args[0]}
                        print(f"[DEBUG] Created tool args from string: {tool_args}")
                else:
                    # Traditional kwargs handling
                    tool_args = kwargs.copy()
                    if args:
                        # If positional args are provided, add them to kwargs
                        tool_args.update({f"arg_{i}": arg for i, arg in enumerate(args)})
                
                # Fix filters parameter - convert dict to JSON string if needed
                if 'filters' in tool_args and isinstance(tool_args['filters'], dict):
                    tool_args['filters'] = json.dumps(tool_args['filters'])
                    print(f"[DEBUG] Converted filters to JSON: {tool_args['filters']}")
                
                # Add debug logging for tool calls
                print(f"[DEBUG] Calling tool {self.name} with final args: {tool_args}")
                
                result = await self.session.call_tool(self.name, tool_args)
                if result.content:
                    # Handle different content types from MCP - use type ignore for flexibility
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        return content.text  # type: ignore
                    elif hasattr(content, 'data'):
                        return str(content.data)  # type: ignore
                    else:
                        return str(content)
                return "Tool executed successfully but returned no content"
            except Exception as e:
                return f"Error calling tool {self.name}: {str(e)}"
        
        def _run(self, *args, **kwargs) -> str:
            """Sync implementation (fallback)"""
            # For sync calls, we need to run the async version
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self._arun(*args, **kwargs))
            except RuntimeError:
                # If no event loop is running, create a new one
                return asyncio.run(self._arun(*args, **kwargs))
else:
    class MCPTool:
        """Placeholder when LangChain is not available"""
        def __init__(self, name: str, description: str, session: ClientSession, schema: Dict[str, Any]):
            self.name = name
            self.description = description
            self.session = session
            self.tool_schema = schema


class LangChainReActAgent:
    """Advanced autonomous agent using LangChain's ReAct pattern with MCP tools"""
    
    def __init__(self, llm_provider: str = "azure"):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required for this agent. Install with: pip install langchain langchain-openai langchainhub")
            
        self.mcp_session: Optional[ClientSession] = None
        self.tools: List[MCPTool] = []
        self.agent_executor: Optional[AgentExecutor] = None
        
        # Initialize LLM
        if llm_provider == "azure":
            self.llm = AzureChatOpenAI(
                azure_deployment=os.getenv("MODEL", "gpt-35-turbo"),
                api_version=os.getenv("AZURE_API_VERSION", "2023-05-15"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT", ""),
                api_key=os.getenv("LLM_API_KEY", ""),  # type: ignore
                temperature=0.1
            )
            print("[INFO] Using Azure OpenAI for LangChain ReAct agent")
        else:
            self.llm = ChatOpenAI(
                base_url=os.getenv("BASE_URL", "https://api.openai.com/v1"),
                api_key=os.getenv("LLM_API_KEY", ""),  # type: ignore
                model=os.getenv("MODEL", "gpt-3.5-turbo"),
                temperature=0.1
            )
            print("[INFO] Using OpenAI for LangChain ReAct agent")
        
        # Initialize memory for conversation history (suppress deprecation warning)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                return_messages=True,
                k=10  # Keep last 10 conversation turns
            )
    
    @asynccontextmanager
    async def mcp_connection(self, server_url: str):
        """Context manager for MCP connection"""
        streams_context = sse_client(url=server_url)
        streams = await streams_context.__aenter__()
        session_context = ClientSession(*streams)
        session = await session_context.__aenter__()
        await session.initialize()
        
        try:
            self.mcp_session = session
            await self._load_mcp_tools()
            yield session
        finally:
            await session_context.__aexit__(None, None, None)
            await streams_context.__aexit__(None, None, None)
            print("[INFO] Closed MCP connection")
    
    async def _load_mcp_tools(self):
        """Load MCP tools and convert them to LangChain tools"""
        if not self.mcp_session:
            print("[WARN] No MCP session available")
            return
        
        print("[INFO] Loading MCP tools...")
        try:
            mcp_tools = await self.mcp_session.list_tools()
            
            if not mcp_tools or not mcp_tools.tools:
                print("[WARN] No MCP tools available")
                return
            
            self.tools = []
            for tool in mcp_tools.tools:
                try:
                    mcp_tool = MCPTool(
                        name=tool.name,
                        description=tool.description or "No description available",
                        session=self.mcp_session,
                        schema=tool.inputSchema
                    )
                    self.tools.append(mcp_tool)
                    print(f"[DEBUG] Created tool: {tool.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to create tool {tool.name}: {e}")
                    continue
            
            print(f"[INFO] Loaded {len(self.tools)} MCP tools: {[t.name for t in self.tools]}")
            
        except Exception as e:
            print(f"[ERROR] Failed to load MCP tools: {e}")
    
    def _create_agent(self):
        """Create the ReAct agent with loaded tools"""
        if not self.tools:
            print("[WARN] No tools available for agent")
            return None
        prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question
Use chat-history to keep context of the conversation.
Begin!

Question: {input}
Thought: {agent_scratchpad}
""")
        
        # Create the ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor with memory
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=10,
            max_execution_time=60,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        print("[INFO] ReAct agent created successfully")
        return self.agent_executor

    async def query(self, user_input: list) -> str:
        """Process user query using the autonomous ReAct agent"""
        if not self.agent_executor:
            self._create_agent()
        
        if not self.agent_executor:
            return "Error: Failed to create agent"
        
        try:
            print(f"\n[AGENT] Processing: {user_input}")
            print("[AGENT] Starting autonomous reasoning and action cycle...\n")
            
            # Run the agent
            
            result = await self.agent_executor.ainvoke({
                "input": user_input,
            })
            
            # Extract the final answer
            final_answer = result.get("output", "No output received")
            
            # Show intermediate steps if available
            if "intermediate_steps" in result:
                print("\n[DEBUG] Agent reasoning steps:")
                for i, (action, observation) in enumerate(result["intermediate_steps"], 1):
                    print(f"  Step {i}: {action.tool} -> {observation[:100]}...")
            
            return final_answer
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
    
    def clear_memory(self):
        """Clear the agent's conversation memory"""
        self.memory.clear()
        print("[INFO] Agent memory cleared")
    
    def get_memory_summary(self) -> str:
        """Get a summary of the agent's memory"""
        try:
            messages = self.memory.chat_memory.messages
            if not messages:
                return "No conversation history"
            
            summary = f"Conversation history ({len(messages)} messages):\n"
            for i, msg in enumerate(messages[-6:], 1):  # Show last 6 messages
                role = "Human" if msg.type == "human" else "Agent"
                content_str = str(msg.content)  # Convert to string to handle different types
                content = content_str[:100] + "..." if len(content_str) > 100 else content_str
                summary += f"  {i}. {role}: {content}\n"
            
            return summary
        except Exception as e:
            return f"Error retrieving memory: {e}"


async def main(mcp_url: str = "http://10.241.89.113:3002/sse"):
    """Interactive chat with LangChain ReAct agent"""
    if not LANGCHAIN_AVAILABLE:
        print("❌ LangChain is not installed. Please install it first:")
        print("pip install langchain langchain-openai langchainhub")
        print("\nAlternatively, use the original MCP agent with: python main.py")
        return
    
    try:
        agent = LangChainReActAgent()
    except ImportError as e:
        print(f"❌ Error initializing agent: {e}")
        return

    async with agent.mcp_connection(mcp_url):
        print("\n🤖 LangChain ReAct Agent Connected! with MCP URL:", mcp_url)
        print(f"🔧 Available tools: {[tool.name for tool in agent.tools]}")
        print("🧠 This agent can autonomously reason and use tools to solve complex problems.")
        print("Commands: 'exit', 'clear' (memory), 'memory' (show history)\n")
        
        while True:
            user_input = input("👉 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("🚀 Exiting...")
                break
            
            if user_input.lower() == 'clear':
                agent.clear_memory()
                continue
            
            if user_input.lower() == 'memory':
                print(f"\n📚 {agent.get_memory_summary()}")
                continue
            
            if not user_input:
                continue
            print(f"\n🧠 Processing your query: {user_input} and memory:{agent.memory.chat_memory.messages}")
            query = "previous conversation: " + agent.get_memory_summary() + " current question: " + user_input
            # Let the agent process the query autonomously
            response = await agent.query(query)
            print(f"\n🤖 Agent: {response}\n")


if __name__ == "__main__":
    mcp_url = os.getenv("MCP_URL", "http://localhost:3002/sse")
    asyncio.run(main(mcp_url=mcp_url))
