from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mcp_client_agent import MCPClient
from session_manager import RedisSessionManager, ChatMessage
from dotenv import load_dotenv
import asyncio
import json
import uuid
import os
from datetime import datetime
import typing
# MCP state
load_dotenv()
mcp_client = MCPClient()
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
        print(f"[ERROR] Failed to connect to MCP server: {e}")
        yield
    finally:
        await mcp_client.close()
        print("[INFO] MCP client closed")

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def get_chat_interface(request: Request):
    global mcp_url, system_prompt
    return templates.TemplateResponse("index_simple.html", {
        "request": request,
        "response": None,
        "mcp_url": mcp_url,
        "system_prompt": system_prompt
    })

# Get chat threads for a session
@app.get("/api/threads")
async def get_threads(session_id: typing.Optional[str] = None):
    """Get all threads for a session"""
    if not session_id:
        session_id = "default"
    
    threads = session_manager.get_user_threads(session_id)
    return JSONResponse({
        "session_id": session_id,
        "threads": threads
    })

# Get messages for a specific thread
@app.get("/api/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str):
    """Get all messages in a thread"""
    messages = session_manager.get_messages(thread_id)
    return JSONResponse({
        "thread_id": thread_id,
        "messages": [msg.to_dict() for msg in messages]
    })

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
async def chat_api(
    message: str = Form(...),
    thread_id: typing.Optional[str] = Form(None),
    session_id: str = Form("default"),
    mcp_url_input: typing.Optional[str] = Form(None),
    system_prompt_input: typing.Optional[str] = Form(None)
):
    """Chat with the agent using threading"""
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

    # Create thread if none provided
    if not thread_id:
        # Generate title from first few words of message
        title_words = message.split()[:4]
        title = " ".join(title_words) + ("..." if len(title_words) == 4 else "")
        thread_id = session_manager.create_thread(
            title=title, 
            user_id=session_id, 
            mcp_url=mcp_url, 
            system_prompt=system_prompt
        )

    if not mcp_session:
        return JSONResponse({"error": "MCP server not connected"}, status_code=500)

    try:
        # Add user message to thread
        session_manager.add_message(thread_id, "user", message)
        
        # Get thread context for system prompt
        thread = session_manager.get_thread(thread_id)
        effective_system_prompt = thread.system_prompt if thread and thread.system_prompt else system_prompt
        
        # Prepare messages with system prompt and thread history
        thread_messages = session_manager.get_messages(thread_id)
        
        # Build conversation context
        conversation_messages = []
        if effective_system_prompt:
            conversation_messages.append({"role": "system", "content": effective_system_prompt})
        
        # Add recent thread history (last 10 messages to avoid token limits)
        for msg in thread_messages[-10:]:
            if msg.role in ["user", "assistant"]:
                conversation_messages.append({"role": msg.role, "content": msg.content})
        
        # Temporarily set messages in client
        original_messages = mcp_client.messages.copy()
        mcp_client.messages = conversation_messages
        
        # Process the query
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=message,
            tool_session_map=tool_session_map
        )
        
        # Restore original messages
        mcp_client.messages = original_messages
        
        # Add assistant response to thread
        session_manager.add_message(thread_id, "assistant", response)
        
        return JSONResponse({
            "response": response,
            "thread_id": thread_id,
            "mcp_url": mcp_url,
            "system_prompt": effective_system_prompt
        })
        
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(f"[ERROR] {error_message}")
        return JSONResponse({
            "error": error_message,
            "thread_id": thread_id,
            "mcp_url": mcp_url,
            "system_prompt": system_prompt
        }, status_code=500)
async def chat_with_agent(request: Request, user_input: str = Form(...), mcp_url_input: str = Form(None), system_prompt_input: str = Form(None)):
    global available_tools, tool_session_map, mcp_session, mcp_url, system_prompt

    # Update system prompt if provided
    if system_prompt_input is not None:
        system_prompt = system_prompt_input
        print(f"[INFO] Updated system prompt: {system_prompt[:50]}..." if system_prompt else "[INFO] Cleared system prompt")

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
            return templates.TemplateResponse("index.html", {
                "request": request,
                "response": error_message,
                "mcp_url": mcp_url,
                "system_prompt": system_prompt
            })

    if not mcp_session:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "response": "Error: MCP server not connected",
            "mcp_url": mcp_url,
            "system_prompt": system_prompt
        })

    try:
        # Add system prompt to the query processing if set
        if system_prompt:
            # Temporarily modify the client's message handling to include system prompt
            original_messages = mcp_client.messages.copy()
            if not mcp_client.messages or mcp_client.messages[0].get("role") != "system":
                mcp_client.messages.insert(0, {"role": "system", "content": system_prompt})
        
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=user_input,
            tool_session_map=tool_session_map
        )
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "response": response,
            "mcp_url": mcp_url,
            "system_prompt": system_prompt
        })
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(f"[ERROR] {error_message}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "response": error_message,
            "mcp_url": mcp_url,
            "system_prompt": system_prompt
        })

# API endpoint for programmatic access
from fastapi import Body
from fastapi.responses import JSONResponse

@app.post("/ask")
async def ask_api(
    query: str = Body(...),
    mcp_url_input: typing.Optional[str] = Body(None),
    system_prompt_input: typing.Optional[str] = Body(None)
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
        # Add system prompt to the query processing if set
        if system_prompt:
            # Temporarily modify the client's message handling to include system prompt
            original_messages = mcp_client.messages.copy()
            if not mcp_client.messages or mcp_client.messages[0].get("role") != "system":
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
    thread_id: typing.Optional[str] = Form(None),
    session_id: str = Form("default"),
    mcp_url_input: typing.Optional[str] = Form(None),
    system_prompt_input: typing.Optional[str] = Form(None)
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

            # Set up client context
            original_messages = mcp_client.messages.copy()
            mcp_client.messages = conversation_messages

            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Processing your request...'})}\n\n"

            # Process query
            response = await mcp_client.process_user_query(
                available_tools=available_tools,
                user_query=message,
                tool_session_map=tool_session_map
            )

            # Restore original messages
            mcp_client.messages = original_messages

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
        print(f"[INFO] WebSocket client disconnected")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"Connection error: {str(e)}"
            }))
        except:
            pass

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
        
        # Set up client context
        original_messages = mcp_client.messages.copy()
        mcp_client.messages = conversation_messages
        
        # Process query
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=message,
            tool_session_map=tool_session_map
        )
        
        # Restore original messages
        mcp_client.messages = original_messages
        
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
