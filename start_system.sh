#!/bin/bash

echo "🚀 Multi-Agent AI System Startup Script"
echo "========================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait a moment for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Test backend connectivity
echo "🔍 Testing backend connectivity..."
sleep 5

# Try to connect to backend
for i in {1..10}; do
    if curl -s http://localhost:8000/ping > /dev/null; then
        echo "✅ Backend is responding!"
        break
    else
        echo "⏳ Attempt $i: Backend not ready yet, waiting..."
        sleep 3
    fi
    
    if [ $i -eq 10 ]; then
        echo "❌ Backend failed to start after 10 attempts"
        echo "📋 Checking logs..."
        docker-compose logs backend
        exit 1
    fi
done

# Test frontend
echo "🔍 Testing frontend..."
sleep 5

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is responding!"
else
    echo "⚠️ Frontend may not be ready yet"
fi

echo ""
echo "🎯 System Status:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Health:   http://localhost:8000/health"
echo ""
echo "📋 To view logs:"
echo "   Backend:  docker-compose logs -f backend"
echo "   Frontend: docker-compose logs -f frontend"
echo ""
echo "🔧 To restart:"
echo "   docker-compose restart"
echo ""
echo "✅ Startup complete!"
