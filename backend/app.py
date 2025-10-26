"""
FastAPI backend for Agentify with PostgreSQL database integration
"""
import os
import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Load environment variables
load_dotenv()

from src.database import init_database, close_database, get_db, check_database_health, AsyncSessionLocal
from src.models import User, ChatThread, ChatMessage, MCPServer, LLMConfiguration, UserPreferences
from src.schemas import (
    LoginRequest, LoginResponse, RegisterRequest, UserResponse,
    ChatRequest, ChatResponse, ChatThreadCreate, ChatThreadResponse,
    MCPServerCreate, MCPServerResponse, MCPServerUpdate,
    LLMConfigurationCreate, LLMConfigurationResponse, LLMConfigurationUpdate,
    MessageResponse, HealthResponse
)
from src.auth import (
    authenticate_user, create_access_token, create_refresh_token, get_current_user, get_current_active_user,
    create_user_session, get_password_hash, cleanup_expired_sessions, verify_token
)
from src.mcp_client import MCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
mcp_client = None
available_tools = []
tool_session_map = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global mcp_client, available_tools, tool_session_map
    
    # Startup
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize MCP client
        llm_provider = os.getenv("LLM_PROVIDER", "azure").lower()
        mcp_client = MCPClient(llm_provider=llm_provider)
        
        # Try to connect to MCP server
        mcp_url = os.getenv("MCP_URL", "http://localhost:8000/sse")
        try:
            async with mcp_client.sse_client_lifecycle(mcp_url) as session:
                mcp_client.session = session
                available_tools = await mcp_client.list_tools()
                tool_session_map = {tool['function']['name']: session for tool in available_tools}
                logger.info(f"Connected to MCP server with {len(available_tools)} tools")
        except Exception as e:
            logger.warning(f"Could not connect to MCP server: {e}")
            available_tools = []
            tool_session_map = {}
        
        # Clean up expired sessions periodically
        async def cleanup_sessions():
            async with AsyncSessionLocal() as db:
                cleaned = await cleanup_expired_sessions(db)
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} expired sessions")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    finally:
        # Shutdown
        try:
            if mcp_client:
                await mcp_client.close()
            await close_database()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

# Create FastAPI app
app = FastAPI(
    title="Agentify API",
    description="Advanced AI Agent Platform with MCP Integration",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Serve React app static files (commented out for development)
# app.mount("/assets", StaticFiles(directory="../frontend/dist/assets"), name="assets")

# Health check endpoint
@app.get("/api/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    db_healthy = await check_database_health()
    
    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        database=db_healthy,
        timestamp=datetime.now()
    )

# Serve React app for all non-API routes
@app.get("/")
@app.get("/config")
@app.get("/login")
@app.get("/register")
async def serve_react_app():
    """Serve the React app for all frontend routes"""
    return FileResponse("../frontend/dist/index.html")

# Authentication endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.username == request.username) | (User.email == request.email)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if existing_user.username == request.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    try:
        # Create new user
        hashed_password = get_password_hash(request.password)
        user = User(
            username=request.username,
            email=request.email,
            full_name=request.full_name,
            hashed_password=hashed_password
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create default preferences
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)
        await db.commit()
        
        logger.info(f"New user registered: {user.username}")
        return UserResponse.model_validate(user)
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return JWT token"""
    user = await authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token and refresh token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Create user session
    await create_user_session(db, user, access_token, request)
    
    # Update last login
    user.last_login = datetime.now()
    await db.commit()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )

@app.post("/api/auth/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    # Create new access and refresh tokens
    access_token = create_access_token(data={"sub": str(current_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(current_user.id)})
    
    # Update user session
    await create_user_session(db, current_user, access_token, request)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(current_user)
    )

@app.post("/api/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate session"""
    # This would require getting the token from the request
    # For now, just return success
    return MessageResponse(message="Logged out successfully")

# User endpoints
@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)

# Chat endpoints
@app.get("/api/threads", response_model=List[ChatThreadResponse])
async def list_chat_threads(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all chat threads for the current user"""
    result = await db.execute(
        select(ChatThread)
        .where(ChatThread.user_id == current_user.id)
        .where(~ChatThread.is_archived)
        .options(selectinload(ChatThread.messages))
        .order_by(ChatThread.updated_at.desc())
    )
    threads = result.scalars().all()
    
    return [ChatThreadResponse.model_validate(thread) for thread in threads]

@app.post("/api/threads", response_model=ChatThreadResponse)
async def create_chat_thread(
    thread_data: ChatThreadCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat thread"""
    thread = ChatThread(
        user_id=current_user.id,
        title=thread_data.title or "New Chat"
    )
    
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    
    return ChatThreadResponse.model_validate(thread)

@app.get("/api/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a specific thread"""
    # Verify thread belongs to user
    result = await db.execute(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.user_id == current_user.id
        )
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    
    return [message.to_dict() for message in messages]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a chat message"""
    global mcp_client, available_tools, tool_session_map
    
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not available")
    
    # Get or create thread
    thread_id = chat_request.thread_id
    if not thread_id:
        # Create new thread with title based on first message
        title_words = chat_request.message.split()[:4]
        title = " ".join(title_words) + ("..." if len(title_words) == 4 else "")
        
        thread = ChatThread(
            user_id=current_user.id,
            title=title
        )
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        thread_id = thread.id
    else:
        # Verify thread belongs to user
        result = await db.execute(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == current_user.id
            )
        )
        thread = result.scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
    
    # Add user message to database
    user_message = ChatMessage(
        thread_id=thread_id,
        role="user",
        content=chat_request.message
    )
    db.add(user_message)
    
    # Get conversation history
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at)
        .limit(20)  # Last 20 messages for context
    )
    messages = result.scalars().all()
    
    # Build conversation context for MCP client
    conversation_messages = []
    for msg in messages:
        conversation_messages.append({"role": msg.role, "content": msg.content})
    
    # Add the new user message
    conversation_messages.append({"role": "user", "content": chat_request.message})
    
    try:
        # Set conversation context
        mcp_client.messages = conversation_messages
        
        # Process with MCP client
        response = await mcp_client.process_user_query(
            available_tools=available_tools,
            user_query=chat_request.message,
            tool_session_map=tool_session_map
        )
        
        # Add assistant response to database
        assistant_message = ChatMessage(
            thread_id=thread_id,
            role="assistant",
            content=response
        )
        db.add(assistant_message)
        
        # Update thread timestamp
        thread.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user_message)
        await db.refresh(assistant_message)
        
        return ChatResponse(
            response=response,
            thread_id=thread_id,
            message_id=assistant_message.id
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.delete("/api/threads/{thread_id}")
async def delete_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat thread"""
    # Verify thread belongs to user
    result = await db.execute(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.user_id == current_user.id
        )
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    await db.delete(thread)
    await db.commit()
    
    return MessageResponse(message="Thread deleted successfully")

# MCP Server management endpoints
@app.get("/api/mcp/servers", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all MCP servers for the current user"""
    result = await db.execute(
        select(MCPServer)
        .where(MCPServer.user_id == current_user.id)
        .order_by(MCPServer.created_at.desc())
    )
    servers = result.scalars().all()
    
    return [MCPServerResponse.model_validate(server) for server in servers]

@app.post("/api/mcp/servers", response_model=MCPServerResponse)
async def create_mcp_server(
    server_data: MCPServerCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new MCP server configuration"""
    server = MCPServer(
        user_id=current_user.id,
        name=server_data.name,
        description=server_data.description,
        server_type=server_data.server_type,
        configuration=server_data.configuration
    )
    
    db.add(server)
    await db.commit()
    await db.refresh(server)
    
    return MCPServerResponse.model_validate(server)

@app.put("/api/mcp/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: uuid.UUID,
    server_data: MCPServerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an MCP server configuration"""
    result = await db.execute(
        select(MCPServer).where(
            MCPServer.id == server_id,
            MCPServer.user_id == current_user.id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Update fields
    if server_data.name is not None:
        server.name = server_data.name
    if server_data.description is not None:
        server.description = server_data.description
    if server_data.server_type is not None:
        server.server_type = server_data.server_type
    if server_data.configuration is not None:
        server.configuration = server_data.configuration
    if server_data.is_active is not None:
        server.is_active = server_data.is_active
    
    await db.commit()
    await db.refresh(server)
    
    return MCPServerResponse.model_validate(server)

@app.delete("/api/mcp/servers/{server_id}")
async def delete_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an MCP server configuration"""
    result = await db.execute(
        select(MCPServer).where(
            MCPServer.id == server_id,
            MCPServer.user_id == current_user.id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    await db.delete(server)
    await db.commit()
    
    return MessageResponse(message="MCP server deleted successfully")

# LLM Configuration endpoints
@app.get("/api/llm/configurations", response_model=List[LLMConfigurationResponse])
async def list_llm_configurations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all LLM configurations for the current user"""
    result = await db.execute(
        select(LLMConfiguration)
        .where(LLMConfiguration.user_id == current_user.id)
        .order_by(LLMConfiguration.is_default.desc(), LLMConfiguration.created_at.desc())
    )
    configurations = result.scalars().all()
    
    return [LLMConfigurationResponse.model_validate(config) for config in configurations]

@app.post("/api/llm/configurations", response_model=LLMConfigurationResponse)
async def create_llm_configuration(
    config_data: LLMConfigurationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new LLM configuration"""
    # If this is set as default, unset other defaults
    if config_data.is_default:
        result_update = await db.execute(
            select(LLMConfiguration)
            .where(LLMConfiguration.user_id == current_user.id)
        )
        existing_configs = result_update.scalars().all()
        for config in existing_configs:
            config.is_default = False
    
    configuration = LLMConfiguration(
        user_id=current_user.id,
        name=config_data.name,
        provider=config_data.provider,
        model_name=config_data.model_name,
        configuration=config_data.configuration,
        is_default=config_data.is_default
    )
    
    db.add(configuration)
    await db.commit()
    await db.refresh(configuration)
    
    return LLMConfigurationResponse.model_validate(configuration)

@app.put("/api/llm/configurations/{config_id}", response_model=LLMConfigurationResponse)
async def update_llm_configuration(
    config_id: uuid.UUID,
    config_data: LLMConfigurationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an LLM configuration"""
    result = await db.execute(
        select(LLMConfiguration).where(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == current_user.id
        )
    )
    configuration = result.scalar_one_or_none()
    
    if not configuration:
        raise HTTPException(status_code=404, detail="LLM configuration not found")
    
    # If setting as default, unset other defaults
    if config_data.is_default:
        result_update = await db.execute(
            select(LLMConfiguration)
            .where(
                LLMConfiguration.user_id == current_user.id,
                LLMConfiguration.id != config_id
            )
        )
        existing_configs = result_update.scalars().all()
        for config in existing_configs:
            config.is_default = False
    
    # Update fields
    if config_data.name is not None:
        configuration.name = config_data.name
    if config_data.provider is not None:
        configuration.provider = config_data.provider
    if config_data.model_name is not None:
        configuration.model_name = config_data.model_name
    if config_data.configuration is not None:
        configuration.configuration = config_data.configuration
    if config_data.is_default is not None:
        configuration.is_default = config_data.is_default
    if config_data.is_active is not None:
        configuration.is_active = config_data.is_active
    
    await db.commit()
    await db.refresh(configuration)
    
    return LLMConfigurationResponse.model_validate(configuration)

@app.delete("/api/llm/configurations/{config_id}")
async def delete_llm_configuration(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an LLM configuration"""
    result = await db.execute(
        select(LLMConfiguration).where(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == current_user.id
        )
    )
    configuration = result.scalar_one_or_none()
    
    if not configuration:
        raise HTTPException(status_code=404, detail="LLM configuration not found")
    
    await db.delete(configuration)
    await db.commit()
    
    return MessageResponse(message="LLM configuration deleted successfully")

# MCP Status endpoint
@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get MCP connection status"""
    global mcp_client
    
    if mcp_client and hasattr(mcp_client, 'session') and mcp_client.session:
        return {
            "status": "connected",
            "tools_count": len(available_tools),
            "tools": [tool.get('function', {}).get('name', 'Unknown') for tool in available_tools[:5]]  # First 5 tools
        }
    else:
        return {
            "status": "disconnected",
            "tools_count": 0,
            "tools": []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
