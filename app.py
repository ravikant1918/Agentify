import os
import uuid
import json
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.mcp_client import MCPClient
from src.session_manager import RedisSessionManager

load_dotenv()
# MCP Client
llm_provider = os.getenv("LLM_PROVIDER", "azure").lower()
mcp_client = MCPClient(llm_provider=llm_provider)
available_tools = []
tool_session_map = {}
mcp_session = None
mcp_url = os.getenv("MCP_URL", "http://localhost:8000")
system_prompt = ""  # Default system prompt

# Session manager
session_manager = RedisSessionManager()
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global available_tools, tool_session_map, mcp_session, mcp_url, system_prompt
    try:
        async with mcp_client.sse_client_lifecycle(mcp_url) as session:
            mcp_client.session = session
            mcp_session = session
            available_tools = await mcp_client.list_tools()
            tool_session_map = {tool['function']['name']: session for tool in available_tools}
            print(f"[INFO] Connected to MCP server with {len(available_tools)} tools at {mcp_url}")
            yield
    except Exception as e:
        print(f"[WARN] Could not connect to MCP server at {mcp_url}: {e}")
        print("[INFO] Starting without MCP server - chat will work but AI responses may be limited")
        mcp_session = None
        available_tools = []
        tool_session_map = {}
        yield
    finally:
        if mcp_session:
            await mcp_client.close()
            print("[INFO] MCP client closed")

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuration Management Routes
@app.get("/config")
async def get_config_interface(request: Request):
    """Render the configuration management interface"""
    return templates.TemplateResponse("config.html", {
        "request": request
    })

@app.get("/api/mcp/servers")
async def list_mcp_servers():
    """List all configured MCP servers"""
    try:
        servers = mcp_client.list_mcp_servers()
        return {"servers": servers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/servers")
async def add_mcp_server(server: Dict[str, Any]):
    """Add a new MCP server configuration"""
    try:
        if mcp_client.add_mcp_server(server["id"], server):
            return {"message": "MCP server added successfully"}
        raise HTTPException(status_code=400, detail="Failed to add MCP server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str):
    """Delete an MCP server configuration"""
    try:
        if mcp_client.remove_mcp_server(server_id):
            return {"message": "MCP server deleted successfully"}
        raise HTTPException(status_code=400, detail="Failed to delete MCP server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/mcp/servers/{server_id}")
async def update_mcp_server(server_id: str, server: Dict[str, Any]):
    """Update an MCP server configuration"""
    try:
        if mcp_client.update_mcp_server(server_id, server):
            return {"message": "MCP server updated successfully"}
        raise HTTPException(status_code=400, detail="Failed to update MCP server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/servers/{server_id}/connect")
async def connect_to_server(server_id: str):
    """Connect to a specific MCP server"""
    try:
        if await mcp_client.connect_to_mcp(server_id):
            return {"message": "Connected to MCP server successfully"}
        raise HTTPException(status_code=400, detail="Failed to connect to MCP server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/servers/{server_id}/disconnect")
async def disconnect_from_server(server_id: str):
    """Disconnect from a specific MCP server"""
    try:
        if await mcp_client.disconnect_from_mcp(server_id):
            return {"message": "Disconnected from MCP server successfully"}
        raise HTTPException(status_code=400, detail="Failed to disconnect from MCP server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get MCP server connection status"""
    try:
        if mcp_session:
            return """
            <div class="h-3 w-3 rounded-full bg-green-500" title="Connected"></div>
            """
        else:
            return """
            <div class="h-3 w-3 rounded-full bg-red-500" title="Disconnected"></div>
            """
    except Exception:
        return """
        <div class="h-3 w-3 rounded-full bg-yellow-500" title="Error"></div>
        """


@app.get("/", response_class=HTMLResponse)
async def get_chat_interface(request: Request):
    """Render the chat interface with threads and messages"""
    thread_id = request.query_params.get("thread_id", None)
    messages = []
    current_thread = None

    if thread_id:
        messages = [msg.to_dict() for msg in session_manager.get_messages(thread_id)]
        current_thread = session_manager.get_thread(thread_id)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "thread_id": thread_id,
        "messages": messages,
        "current_thread": current_thread,
        "mcp_url": mcp_url,
        "system_prompt": system_prompt
    })

# Thread Management
@app.get("/api/threads")
async def list_threads():
    """List all chat threads for display in the sidebar"""
    try:
        threads = session_manager.get_all_threads()
        return [{
            "id": thread.thread_id,
            "title": thread.title or "New Chat",
            "message_count": len(thread.messages),
            "last_message": thread.messages[-1].content[:100] + "..." if thread.messages else "",
            "updated_at": thread.updated_at
        } for thread in threads]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/threads/sidebar")
async def list_threads_sidebar(request: Request):
    """List all chat threads as HTML for sidebar display"""
    try:
        threads = session_manager.get_all_threads()
        # Get current thread ID from query params or from the main page context
        current_thread_id = request.query_params.get("current_thread_id")

        return templates.TemplateResponse(
            "partials/thread_list.html",
            {
                "request": request,
                "threads": [{
                    "id": thread.thread_id,
                    "title": thread.title or "New Chat",
                    "message_count": len(thread.messages),
                    "last_message": thread.messages[-1].content[:100] + "..." if thread.messages else "",
                    "updated_at": thread.updated_at
                } for thread in threads],
                "current_thread_id": current_thread_id
            }
        )
    except Exception as e:
        print(f"[ERROR] Failed to load thread sidebar: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": f"Failed to load threads: {str(e)}"
            },
            status_code=500
        )

@app.get("/api/threads/{thread_id}/messages")
async def get_thread_messages_html(thread_id: str, request: Request):
    """Get all messages in a thread as HTML for HTMX"""
    if thread_id == "None" or not thread_id:
        # Return empty messages HTML for new threads
        return templates.TemplateResponse(
            "partials/messages.html",
            {
                "request": request,
                "messages": [],
                "thread_id": None
            }
        )

    try:
        messages = session_manager.get_messages(thread_id)
        return templates.TemplateResponse(
            "partials/messages.html",
            {
                "request": request,
                "messages": messages,
                "thread_id": thread_id
            }
        )
    except Exception as e:
        print(f"[ERROR] Failed to get messages for thread {thread_id}: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": f"Failed to load messages: {str(e)}"
            },
            status_code=500
        )

# Create a new thread
@app.post("/api/threads")
async def create_thread(session_id: str = Form(...), title: str = Form("New Chat")):
    """Create a new chat thread"""
    thread_id = session_manager.create_thread(title=title, user_id=session_id, mcp_url=mcp_url, system_prompt=system_prompt)
    return JSONResponse({
        "thread_id": thread_id,
        "title": title
    })

# Update thread title
@app.patch("/api/threads/{thread_id}")
async def update_thread(thread_id: str, title: str = Form(...), session_id: str = Form("default")):
    """Update thread title"""
    session_manager.update_thread_title(thread_id, title, session_id)
    return JSONResponse({"success": True})

# Delete a thread
@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str, session_id: str = Form("default")):
    """Delete a thread and all its messages"""
    session_manager.delete_thread(thread_id, session_id)
    return JSONResponse({"success": True})



# Enhanced chat endpoint with threading support
@app.post("/api/chat")
async def chat_api(request: Request, message: str = Form(...), thread_id: Optional[str] = Form(None)):
    """Process a chat message with HTMX support"""
    if not message.strip():
        if "HX-Request" in request.headers:
            return templates.TemplateResponse(
                "partials/error.html",
                {
                    "request": request,
                    "error": "Message cannot be empty"
                },
                status_code=400
            )
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Create thread if it doesn't exist
    thread = session_manager.get_thread(thread_id)
    if not thread:
        title_words = message.split()[:4]
        title = " ".join(title_words) + ("..." if len(title_words) == 4 else "")
        session_manager.create_thread(title=title, user_id="default", mcp_url=mcp_url, system_prompt=system_prompt, thread_id=thread_id)
    
    # Add user message to thread
    session_manager.add_message(thread_id, "user", message)
    
    # Get thread context
    thread = session_manager.get_thread(thread_id)
    
    # Build conversation context
    messages = session_manager.get_messages(thread_id)
    conversation_messages = []
    
    # Create enhanced system prompt with tool information
    tool_info = ""
    if available_tools:
        tool_names = [tool['function']['name'] for tool in available_tools]
        tool_info = f"\n\nYou have access to the following tools: {', '.join(tool_names)}. When users ask about tools or capabilities, mention these specific tools that are available to you."
    
    effective_system_prompt = (thread.system_prompt if thread and thread.system_prompt else system_prompt) + tool_info
    
    if effective_system_prompt:
        conversation_messages.append({"role": "system", "content": effective_system_prompt})
    
    # Add recent thread history (last 10 messages)
    for msg in messages[-10:]:
        if msg.role in ["user", "assistant"]:
            conversation_messages.append({"role": msg.role, "content": msg.content})
    
    # Set conversation context in MCP client
    mcp_client.messages = conversation_messages
    
    try:
        # Process query
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=message,
            tool_session_map=tool_session_map
        )
        
        # Add assistant response to thread
        session_manager.add_message(thread_id, "assistant", response)
        
        # If this is an HTMX request, return HTML partial
        if "HX-Request" in request.headers:
            messages = session_manager.get_messages(thread_id)[-2:]  # Get the last 2 messages (user + assistant)
            return templates.TemplateResponse(
                "partials/messages.html",
                {
                    "request": request,
                    "messages": messages,
                    "thread_id": thread_id
                }
            )
        
        # For regular API requests, return JSON
        return {
            "thread_id": thread_id,
            "response": response
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Chat API error: {error_msg}")
        
        # Add error response to thread so user can see what happened
        error_response = f"I encountered an error: {error_msg}"
        session_manager.add_message(thread_id, "assistant", error_response)
        
        if "HX-Request" in request.headers:
            messages = session_manager.get_messages(thread_id)[-2:]  # Get the last 2 messages (user + assistant)
            return templates.TemplateResponse(
                "partials/messages.html",
                {
                    "request": request,
                    "messages": messages,
                    "thread_id": thread_id
                }
            )
        
        raise HTTPException(status_code=500, detail=error_msg)
# API endpoint for programmatic access

@app.post("/ask")
async def ask_api(
    query: str = Body(...),
    mcp_url_input: Optional[str] = Body(None),
    system_prompt_input: Optional[str] = Body(None)
):
    global available_tools, tool_session_map, mcp_session, mcp_url, system_prompt

    # Update system prompt if provided
    if system_prompt_input is not None:
        system_prompt = system_prompt_input

    # If user provided a new MCP URL, reconnect
    if mcp_url_input and mcp_url_input != mcp_url:
        mcp_url = mcp_url_input
        try:
            async with mcp_client.sse_client_lifecycle(mcp_url) as session:
                mcp_client.session = session
                mcp_session = session
                available_tools = await mcp_client.list_tools()
                tool_session_map = {tool['function']['name']: session for tool in available_tools}
                print(f"[INFO] Switched to MCP server: {mcp_url}")
        except Exception as e:
            error_message = f"Error connecting to MCP server: {str(e)}"
            print(f"[ERROR] {error_message}")
            return JSONResponse({"error": error_message}, status_code=500)

    if not mcp_session:
        return JSONResponse({"error": "MCP server not connected"}, status_code=500)

    try:
        # Add system prompt if needed
        if system_prompt and (not mcp_client.messages or mcp_client.messages[0].get("role") != "system"):
            mcp_client.messages.insert(0, {"role": "system", "content": system_prompt})
        
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=query,
            tool_session_map=tool_session_map
        )
        return JSONResponse({
            "response": response, 
            "mcp_url": mcp_url,
            "system_prompt": system_prompt
        })
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(f"[ERROR] {error_message}")
        return JSONResponse({
            "error": error_message, 
            "mcp_url": mcp_url,
            "system_prompt": system_prompt
        }, status_code=500)

# Configuration update endpoint
@app.post("/update_config")
async def update_config(
    mcp_url_new: str = Body(..., alias="mcp_url"),
    system_prompt_new: str = Body("", alias="system_prompt")
):
    global available_tools, tool_session_map, mcp_session, mcp_url, system_prompt
    
    try:
        # Update system prompt
        system_prompt = system_prompt_new
        print(f"[INFO] Updated system prompt: {system_prompt[:50]}..." if system_prompt else "[INFO] Cleared system prompt")
        
        # Update MCP URL if different
        if mcp_url_new and mcp_url_new != mcp_url:
            mcp_url = mcp_url_new
            # Reconnect to new MCP server
            async with mcp_client.sse_client_lifecycle(mcp_url) as session:
                mcp_client.session = session
                mcp_session = session
                available_tools = await mcp_client.list_tools()
                tool_session_map = {tool['function']['name']: session for tool in available_tools}
                print(f"[INFO] Switched to MCP server: {mcp_url}")
        
        return JSONResponse({
            "success": True,
            "mcp_url": mcp_url,
            "system_prompt": system_prompt,
            "message": "Configuration updated successfully"
        })
        
    except Exception as e:
        error_message = f"Error updating configuration: {str(e)}"
        print(f"[ERROR] {error_message}")
        return JSONResponse({
            "success": False,
            "error": error_message
        }, status_code=500)

# Streaming chat endpoint
@app.post("/api/chat/stream")
async def chat_stream(
    message: str = Form(...),
    thread_id: Optional[str] = Form(None),
    session_id: str = Form("default"),
    mcp_url_input: Optional[str] = Form(None),
    system_prompt_input: Optional[str] = Form(None)
):
    """Stream chat responses for real-time interaction"""
    global available_tools, tool_session_map, mcp_session, mcp_url, system_prompt

    async def generate_response():
        global available_tools, tool_session_map, mcp_session, mcp_url, system_prompt
        
        try:
            # Update system prompt if provided
            if system_prompt_input is not None:
                system_prompt = system_prompt_input

            # Handle MCP URL changes
            if mcp_url_input and mcp_url_input != mcp_url:
                mcp_url = mcp_url_input
                try:
                    async with mcp_client.sse_client_lifecycle(mcp_url) as session:
                        mcp_client.session = session
                        mcp_session = session
                        available_tools = await mcp_client.list_tools()
                        tool_session_map = {tool['function']['name']: session for tool in available_tools}
                        yield f"data: {json.dumps({'type': 'system', 'content': f'Connected to MCP server: {mcp_url}'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Error connecting to MCP server: {str(e)}'})}\n\n"
                    return

            # Create or get thread
            current_thread_id = thread_id
            if not current_thread_id:
                title_words = message.split()[:4]
                title = " ".join(title_words) + ("..." if len(title_words) == 4 else "")
                current_thread_id = session_manager.create_thread(
                    title=title, 
                    user_id=session_id, 
                    mcp_url=mcp_url, 
                    system_prompt=system_prompt
                )
                yield f"data: {json.dumps({'type': 'thread_created', 'thread_id': current_thread_id})}\n\n"

            if not mcp_session:
                yield f"data: {json.dumps({'type': 'error', 'content': 'MCP server not connected'})}\n\n"
                return

            # Add user message
            session_manager.add_message(current_thread_id, "user", message)
            yield f"data: {json.dumps({'type': 'user_message', 'content': message})}\n\n"

            # Get thread context
            thread = session_manager.get_thread(current_thread_id)
            effective_system_prompt = thread.system_prompt if thread and thread.system_prompt else system_prompt
            
            # Build conversation context
            thread_messages = session_manager.get_messages(current_thread_id)
            conversation_messages = []
            if effective_system_prompt:
                conversation_messages.append({"role": "system", "content": effective_system_prompt})
            
            for msg in thread_messages[-10:]:
                if msg.role in ["user", "assistant"]:
                    conversation_messages.append({"role": msg.role, "content": msg.content})

            # Set conversation context
            mcp_client.messages = conversation_messages

            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Processing your request...'})}\n\n"

            # Process query
            response = await mcp_client.process_user_query(
                available_tools=available_tools,
                user_query=message,
                tool_session_map=tool_session_map
            )

            # Add response to thread
            session_manager.add_message(current_thread_id, "assistant", response)

            # Stream the response
            yield f"data: {json.dumps({'type': 'assistant_message', 'content': response, 'thread_id': current_thread_id})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            print(f"[ERROR] {error_message}")
            yield f"data: {json.dumps({'type': 'error', 'content': error_message})}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    # Store connection-specific data
    connection_data = {
        "session_id": "default",
        "thread_id": None,
        "mcp_url": mcp_url,
        "system_prompt": system_prompt
    }
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": "Invalid JSON format"
                }))
                continue
            
            message_type = message_data.get("type")
            
            if message_type == "config":
                # Update connection configuration
                connection_data["session_id"] = message_data.get("session_id", "default")
                connection_data["thread_id"] = message_data.get("thread_id")
                if message_data.get("mcp_url"):
                    connection_data["mcp_url"] = message_data["mcp_url"]
                if "system_prompt" in message_data:
                    connection_data["system_prompt"] = message_data["system_prompt"]
                
                await websocket.send_text(json.dumps({
                    "type": "config_updated",
                    "config": connection_data
                }))
                
            elif message_type == "chat":
                # Handle chat message
                message = message_data.get("message", "")
                if not message.strip():
                    continue
                
                await handle_websocket_chat(
                    websocket=websocket,
                    message=message,
                    connection_data=connection_data
                )
                
            elif message_type == "get_threads":
                # Get threads for session
                threads = session_manager.get_user_threads(connection_data["session_id"])
                await websocket.send_text(json.dumps({
                    "type": "threads",
                    "threads": threads
                }))
                
            elif message_type == "get_messages":
                # Get messages for current thread
                if connection_data["thread_id"]:
                    messages = session_manager.get_messages(connection_data["thread_id"])
                    await websocket.send_text(json.dumps({
                        "type": "messages",
                        "thread_id": connection_data["thread_id"],
                        "messages": [msg.to_dict() for msg in messages]
                    }))
                
            elif message_type == "create_thread":
                # Create new thread
                title = message_data.get("title", "New Chat")
                thread_id = session_manager.create_thread(
                    title=title,
                    user_id=connection_data["session_id"],
                    mcp_url=connection_data["mcp_url"],
                    system_prompt=connection_data["system_prompt"]
                )
                connection_data["thread_id"] = thread_id
                
                await websocket.send_text(json.dumps({
                    "type": "thread_created",
                    "thread_id": thread_id,
                    "title": title
                }))
                
            elif message_type == "switch_thread":
                # Switch to different thread
                connection_data["thread_id"] = message_data.get("thread_id")
                
                await websocket.send_text(json.dumps({
                    "type": "thread_switched",
                    "thread_id": connection_data["thread_id"]
                }))
                
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"Connection error: {str(e)}"
            }))
        except Exception as send_error:
            print(f"[ERROR] Failed to send error message: {send_error}")

async def handle_websocket_chat(websocket: WebSocket, message: str, connection_data: dict):
    """Handle chat message through WebSocket"""
    global available_tools, tool_session_map, mcp_session
    
    try:
        # Create thread if none exists
        if not connection_data["thread_id"]:
            title_words = message.split()[:4]
            title = " ".join(title_words) + ("..." if len(title_words) == 4 else "")
            connection_data["thread_id"] = session_manager.create_thread(
                title=title,
                user_id=connection_data["session_id"],
                mcp_url=connection_data["mcp_url"],
                system_prompt=connection_data["system_prompt"]
            )
            
            await websocket.send_text(json.dumps({
                "type": "thread_created",
                "thread_id": connection_data["thread_id"],
                "title": title
            }))
        
        # Check MCP connection
        if not mcp_session:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "MCP server not connected"
            }))
            return
        
        # Add user message to thread
        session_manager.add_message(connection_data["thread_id"], "user", message)
        
        # Send user message confirmation
        await websocket.send_text(json.dumps({
            "type": "user_message",
            "content": message,
            "thread_id": connection_data["thread_id"]
        }))
        
        # Send thinking status
        await websocket.send_text(json.dumps({
            "type": "thinking",
            "content": "Processing your request..."
        }))
        
        # Get thread context
        thread = session_manager.get_thread(connection_data["thread_id"])
        effective_system_prompt = (
            thread.system_prompt if thread and thread.system_prompt 
            else connection_data["system_prompt"]
        )
        
        # Build conversation context
        thread_messages = session_manager.get_messages(connection_data["thread_id"])
        conversation_messages = []
        if effective_system_prompt:
            conversation_messages.append({"role": "system", "content": effective_system_prompt})
        
        # Add recent thread history (last 10 messages)
        for msg in thread_messages[-10:]:
            if msg.role in ["user", "assistant"]:
                conversation_messages.append({"role": msg.role, "content": msg.content})
        
        # Set conversation context and process query
        mcp_client.messages = conversation_messages
        
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=message,
            tool_session_map=tool_session_map
        )
        
        # Add response to thread
        session_manager.add_message(connection_data["thread_id"], "assistant", response)
        
        # Send assistant response
        await websocket.send_text(json.dumps({
            "type": "assistant_message",
            "content": response,
            "thread_id": connection_data["thread_id"]
        }))
        
        # Send completion status
        await websocket.send_text(json.dumps({
            "type": "done"
        }))
        
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(f"[ERROR] {error_message}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": error_message
        }))
