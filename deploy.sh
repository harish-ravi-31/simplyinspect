#!/bin/bash

# SimplyInspect Deployment Script

echo "SimplyInspect Deployment"
echo "========================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration before proceeding."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "Building and starting SimplyInspect..."

# Build and start containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo ""
echo "SimplyInspect is starting..."
echo "UI will be available at: http://localhost:3001"
echo "API will be available at: http://localhost:8000"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"