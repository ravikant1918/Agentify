#!/bin/bash

echo "🚀 Deploying Agentify with PostgreSQL and React Frontend..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file with default values..."
    cat > .env << EOF
# Database Configuration
POSTGRES_DB=agentify
POSTGRES_USER=agentify_user
POSTGRES_PASSWORD=agentify_pass_$(openssl rand -hex 8)

# JWT Configuration
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM Configuration
LLM_PROVIDER=azure
MODEL=gpt-4
AZURE_API_VERSION=2024-12-01-preview
AZURE_ENDPOINT=https://your-endpoint.openai.azure.com/
LLM_API_KEY=your-azure-api-key

# Optional: Google Gemini
GOOGLE_API_KEY=
GOOGLE_MODELS=gemini-2.0-flash-exp

# Optional: OpenAI
BASE_URL=https://api.openai.com/v1

# MCP Configuration
MCP_URL=http://localhost:8000/sse

# Application
PORT=8001
EOF
    echo "⚠️  Please edit .env file with your actual API keys and endpoints!"
    echo "📍 Generated secure passwords and JWT secret"
fi

# Build React frontend if not already built
if [ ! -d "frontend/dist" ]; then
    echo "🏗️  Building React frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo "✅ React frontend already built"
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Remove old images to ensure fresh build
echo "🧹 Cleaning up old images..."
docker-compose down --rmi local 2>/dev/null || true

# Build and start the application
echo "🏗️  Building and starting the application..."
docker-compose up --build -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 20

# Check PostgreSQL
echo "🗄️  Checking PostgreSQL connection..."
if docker-compose exec -T postgres pg_isready -U agentify_user -d agentify > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL connection failed"
    echo "📋 Check logs with: docker-compose logs postgres"
fi

# Check Redis
echo "📦 Checking Redis connection..."
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis connection failed"
    echo "📋 Check logs with: docker-compose logs redis"
fi

# Check if the application is running
echo "🌐 Checking application status..."
if curl -f http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
    echo ""
    echo "� Agentify is now deployed!"
    echo "�🌐 Access the application at: http://localhost:8001/"
    echo "� API documentation at: http://localhost:8001/docs"
    echo "🗄️  PostgreSQL: localhost:5432 (agentify/agentify_user)"
    echo "� Redis: localhost:6379"
    echo ""
    echo "🧪 Test the API:"
    echo "curl -X GET http://localhost:8001/api/health"
    echo ""
    echo "👤 Create your first user account via the web interface!"
else
    echo "❌ Application failed to start properly"
    echo "📋 Check logs with: docker-compose logs agentify"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "1. Check if all services are running: docker-compose ps"
    echo "2. View application logs: docker-compose logs agentify"
    echo "3. Check database logs: docker-compose logs postgres"
    echo "4. Verify environment variables in .env file"
fi

echo ""
echo "🔧 Useful commands:"
echo "  View all logs:     docker-compose logs -f"
echo "  View app logs:     docker-compose logs -f agentify"
echo "  View DB logs:      docker-compose logs -f postgres"
echo "  Stop application:  docker-compose down"
echo "  Restart:           docker-compose restart"
echo "  Rebuild:           docker-compose up --build"
echo "  Clean restart:     docker-compose down && docker-compose up --build"
echo ""
echo "📊 Service Status:"
docker-compose ps
