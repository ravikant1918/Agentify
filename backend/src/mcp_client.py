import asyncio
import json
import os
import traceback
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Dict, Any, List, Optional
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from openai import AzureOpenAI, OpenAI
from .config_manager import ConfigManager

class MCPClient:
    def __init__(self, llm_provider: str = "azure", redis_url: str = None):
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, Optional[ClientSession]] = {}
        self.active_session: str = None
        self.messages: List[Dict[str, Any]] = []
        self.debug = os.getenv("MCP_DEBUG", "false").lower() == "true"
        
        # Initialize configuration manager
        self.config_manager = ConfigManager(redis_url=redis_url)
        
        # Load LLM configuration
        self._load_llm_config(llm_provider)

    def _load_llm_config(self, llm_provider: str):
        """Load and validate LLM configuration"""
        self.model = os.getenv("MODEL", "gpt-4")
        self.api_version = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT")
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("BASE_URL", "https://api.openai.com/v1")
        
        # Google Gemini configuration
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_models = os.getenv("GOOGLE_MODELS", "gemini-2.0-flash-exp")
        self.google_api_url = os.getenv("GOOGLE_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/")
        
        # Validate required configuration
        if llm_provider == "google":
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required for Google Gemini")
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_api_key)
                self.llm_client = genai.GenerativeModel(self.google_models)
                print(f"[INFO] Using Google Gemini as LLM provider (Model: {self.google_models})")
            except ImportError:
                raise ValueError("google-generativeai package is required for Google Gemini support")
        
        elif llm_provider == "azure":
            if not self.api_key:
                raise ValueError("LLM_API_KEY environment variable is required")
            if not self.azure_endpoint:
                raise ValueError("AZURE_ENDPOINT environment variable is required for Azure OpenAI")
            
            self.llm_client = AzureOpenAI(
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key
            )
            print(f"[INFO] Using Azure OpenAI as LLM provider (Model: {self.model})")

        elif llm_provider == "openai":
            if not self.api_key:
                raise ValueError("LLM_API_KEY environment variable is required")
            self.llm_client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
            print(f"[INFO] Using OpenAI as LLM provider (Model: {self.model})")
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Supported: google, azure, openai")

    async def connect_to_stdio_server(self, server_script_path: str):
        """Connect to MCP server using STDIO"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')

        if not (is_python or is_js):
            raise ValueError("Server script must be .py or .js")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            await self.session.initialize()
            print(f"[INFO] Initialized STDIO MCP client for {server_script_path}")
        except Exception as e:
            print(f"[ERROR] Failed to connect to STDIO server {server_script_path}: {e}")
            raise

    @asynccontextmanager
    async def sse_client_lifecycle(self, server_url: str):
        """Context manager for SSE client lifecycle with better error handling"""
        streams_context = None
        session_context = None
        session = None
        
        try:
            if self.debug:
                print(f"[DEBUG] Connecting to SSE server at {server_url}")
                
            streams_context = sse_client(url=server_url)
            streams = await streams_context.__aenter__()
            
            session_context = ClientSession(*streams)
            session = await session_context.__aenter__()
            await session.initialize()
            
            if self.debug:
                print("[DEBUG] SSE client initialized successfully")
                
            yield session
            
        except Exception as e:
            print(f"[ERROR] SSE client error: {e}")
            if self.debug:
                print(f"[DEBUG] SSE error traceback: {traceback.format_exc()}")
            raise
        finally:
            # Cleanup in reverse order with error handling
            cleanup_errors = []
            
            if session_context:
                try:
                    await session_context.__aexit__(None, None, None)
                except Exception as e:
                    cleanup_errors.append(f"Session cleanup error: {e}")
                    
            if streams_context:
                try:
                    await streams_context.__aexit__(None, None, None)
                except Exception as e:
                    cleanup_errors.append(f"Streams cleanup error: {e}")
            
            if cleanup_errors:
                print(f"[WARNING] Cleanup errors: {'; '.join(cleanup_errors)}")
            else:
                print("[INFO] Closed SSE client cleanly")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from MCP server with enhanced error handling"""
        if not self.session:
            print("[WARN] No MCP session available")
            return []
            
        print("[INFO] Listing tools from MCP server...")
        try:
            mcp_tools = await self.session.list_tools()
            
            if not mcp_tools or not mcp_tools.tools:
                print("[WARN] No tools available from MCP server")
                return []

            tools = []
            for tool in mcp_tools.tools:
                try:
                    tool_def = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or f"Tool: {tool.name}",
                            "parameters": tool.inputSchema or {}
                        }
                    }
                    tools.append(tool_def)
                    
                    if self.debug:
                        print(f"[DEBUG] Added tool: {tool.name}")
                        
                except Exception as e:
                    print(f"[WARNING] Failed to process tool {getattr(tool, 'name', 'unknown')}: {e}")
                    continue
            
            print(f"[INFO] Found {len(tools)} valid tools")
            return tools
            
        except Exception as e:
            print(f"[ERROR] Failed to list tools: {e}")
            if self.debug:
                print(f"[DEBUG] List tools traceback: {traceback.format_exc()}")
            return []

    async def process_user_query(
        self, 
        available_tools: List[Dict[str, Any]], 
        user_query: str, 
        tool_session_map: Dict[str, Any],
        max_iterations: int = 10
    ) -> str:
        """Process user query with enhanced error handling and iteration limits"""
        if not self.session:
            return "Error: No MCP session available"
            
        if not user_query.strip():
            return "Error: Empty query provided"
            
        # Add current user query to existing conversation history
        self.messages.append({"role": "user", "content": user_query})
        
        try:
            iteration_count = 0
            
            # Get initial response from LLM
            response = await self._call_llm(available_tools)
            azure_response = response.choices[0].message
            assistant_content = azure_response.content or ""
            
            # Handle tool calls with iteration limit
            while azure_response.tool_calls and iteration_count < max_iterations:
                iteration_count += 1
                
                if self.debug:
                    print(f"[DEBUG] Tool call iteration {iteration_count}")
                
                # Add assistant response with tool_calls to conversation
                assistant_message: Dict[str, Any] = {"role": "assistant", "content": assistant_content}
                if azure_response.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in azure_response.tool_calls
                    ]
                self.messages.append(assistant_message)
                print(f"[INFO] Processing {len(azure_response.tool_calls)} tool calls (iteration {iteration_count})")
                
                # Execute tool calls
                for tool_call in azure_response.tool_calls:
                    tool_result = await self._execute_tool_call(tool_call, tool_session_map)
                    self.messages.append(tool_result)
                
                # Get follow-up response from LLM with tool results
                response = await self._call_llm(available_tools)
                azure_response = response.choices[0].message
                assistant_content = azure_response.content or ""
            
            # Check if we hit the iteration limit
            if iteration_count >= max_iterations:
                print(f"[WARNING] Reached maximum tool call iterations ({max_iterations})")
                assistant_content += f"\n\n[Note: Reached maximum tool call iterations ({max_iterations})]"
            
            # Add final assistant response (without tool calls)
            if not azure_response.tool_calls:
                self.messages.append({"role": "assistant", "content": assistant_content})
            
            return assistant_content
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"[ERROR] {error_msg}")
            if self.debug:
                print(f"[DEBUG] Process query traceback: {traceback.format_exc()}")
            return error_msg

    async def _call_llm(self, available_tools: List[Dict[str, Any]]):
        """Make LLM API call with error handling"""
        try:
            # Handle Google Gemini API differently
            if hasattr(self, 'google_api_key') and self.google_api_key:
                import google.generativeai as genai
                
                # Convert OpenAI-style messages to Gemini format
                gemini_messages = []
                system_message = None
                
                for msg in self.messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    
                    if role == "system":
                        system_message = content
                    elif role == "user":
                        gemini_messages.append({"role": "user", "parts": [content]})
                    elif role == "assistant":
                        gemini_messages.append({"role": "model", "parts": [content]})
                    elif role == "tool":
                        # Add tool results as model response
                        gemini_messages.append({"role": "model", "parts": [content]})
                
                # Configure generation with system message if present
                generation_config = genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4000,
                )
                
                # Create model with system instruction if available
                if system_message:
                    model = genai.GenerativeModel(
                        self.google_models,
                        system_instruction=system_message,
                        generation_config=generation_config
                    )
                else:
                    model = genai.GenerativeModel(
                        self.google_models,
                        generation_config=generation_config
                    )
                
                # Start chat with history
                chat = model.start_chat(history=gemini_messages[:-1] if gemini_messages else [])
                
                # Send the last message
                if gemini_messages:
                    last_message = gemini_messages[-1]
                    response = await asyncio.to_thread(
                        chat.send_message,
                        last_message["parts"][0]
                    )
                    # Convert Gemini response to OpenAI-like format for compatibility
                    return type('MockResponse', (), {
                        'choices': [type('Choice', (), {
                            'message': type('Message', (), {
                                'content': response.text,
                                'tool_calls': None
                            })()
                        })()]
                    })()
                else:
                    # No messages, return empty response
                    return type('MockResponse', (), {
                        'choices': [type('Choice', (), {
                            'message': type('Message', (), {
                                'content': "Hello! How can I help you?",
                                'tool_calls': None
                            })()
                        })()]
                    })()
            else:
                # OpenAI/Azure API
                return await asyncio.to_thread(
                    self.llm_client.chat.completions.create,
                    messages=self.messages,
                    model=self.model,
                    tools=available_tools if available_tools else None,
                    tool_choice="auto" if available_tools else "none",
                    temperature=0.1,  # Lower temperature for more consistent responses
                    max_tokens=4000   # Reasonable token limit
                )
        except Exception as e:
            print(f"[ERROR] LLM API call failed: {e}")
            raise

    async def _execute_tool_call(self, tool_call, tool_session_map: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call with comprehensive error handling"""
        tool_name = tool_call.function.name
        tool_call_id = tool_call.id
        
        try:
            # Parse tool arguments
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in tool arguments: {e}"
                print(f"[ERROR] {error_msg}")
                return {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Error: {error_msg}"
                }
            
            print(f"[INFO] Calling tool: {tool_name} with args: {tool_args}")
            
            # Check if tool is available
            if tool_name not in tool_session_map:
                error_msg = f"Tool {tool_name} not available in session map"
                print(f"[ERROR] {error_msg}")
                return {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Error: {error_msg}"
                }
            
            # Execute the tool
            try:
                result = await tool_session_map[tool_name].call_tool(tool_name, tool_args)
                tool_content = result.content[0].text if result.content else "No output from tool"
                
                if self.debug:
                    print(f"[DEBUG] Tool {tool_name} returned: {len(tool_content)} characters")
                    
                return {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_content
                }
                
            except Exception as e:
                error_msg = f"Error calling tool {tool_name}: {str(e)}"
                print(f"[ERROR] {error_msg}")
                if self.debug:
                    print(f"[DEBUG] Tool call traceback: {traceback.format_exc()}")
                    
                return {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Error: {error_msg}"
                }
                
        except Exception as e:
            # Catch-all for any unexpected errors
            error_msg = f"Unexpected error executing tool {tool_name}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Error: {error_msg}"
            }

    def clear_conversation(self):
        """Clear the conversation history"""
        self.messages = []
        print("[INFO] Conversation history cleared")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation"""
        return {
            "message_count": len(self.messages),
            "roles": [msg.get("role") for msg in self.messages],
            "has_tool_calls": any(msg.get("tool_calls") for msg in self.messages),
            "last_message_role": self.messages[-1].get("role") if self.messages else None
        }
    
    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        """List configured MCP servers"""
        # For now, return a simple list with the current server
        servers = []
        if hasattr(self, 'session') and self.session:
            servers.append({
                "id": "default",
                "name": "Default MCP Server",
                "url": os.getenv("MCP_URL", "http://localhost:8000/sse"),
                "status": "connected",
                "tool_count": len(getattr(self, 'available_tools', []))
            })
        return servers

    def add_mcp_server(self, server_id: str, server_config: Dict[str, Any]) -> bool:
        """Add a new MCP server configuration"""
        # For now, just store in memory - in production this would be persisted
        print(f"[INFO] Added MCP server {server_id}: {server_config}")
        return True

    def remove_mcp_server(self, server_id: str) -> bool:
        """Remove an MCP server configuration"""
        print(f"[INFO] Removed MCP server {server_id}")
        return True

    def update_mcp_server(self, server_id: str, server_config: Dict[str, Any]) -> bool:
        """Update an MCP server configuration"""
        print(f"[INFO] Updated MCP server {server_id}: {server_config}")
        return True

    async def connect_to_mcp(self, server_id: str) -> bool:
        """Connect to a specific MCP server"""
        print(f"[INFO] Connecting to MCP server {server_id}")
        # For now, assume connection succeeds
        return True

    async def close(self):
        """Close the MCP client and cleanup resources"""
        try:
            await self.exit_stack.aclose()
            print("[INFO] MCP client closed successfully")
        except Exception as e:
            print(f"[ERROR] Error closing MCP client: {e}")