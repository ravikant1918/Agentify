#!/bin/bash

echo "🚀 Deploying Fast Agent PoC..."

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose down

# Build and start the application
echo "Building and starting the application..."
docker-compose up --build -d

# Wait for the application to start
echo "Waiting for application to start..."
sleep 10

# Check if the application is running
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
    echo "🌐 Access the chat interface at: http://localhost:8000/"
    echo "📡 API endpoint available at: http://localhost:8000/ask"
    echo ""
    echo "📋 Test the API with:"
    echo 'curl -X POST http://localhost:8000/ask \\'
    echo '  -H "Content-Type: application/json" \\'
    echo '  -d '"'"'{"query": "Hello, how are you?"}'"'"''
else
    echo "❌ Application failed to start properly"
    echo "📋 Check logs with: docker-compose logs"
fi

echo ""
echo "🔧 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop app:  docker-compose down"
echo "  Rebuild:   docker-compose up --build"
