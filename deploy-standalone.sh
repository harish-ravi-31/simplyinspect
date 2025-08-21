#!/bin/bash

# SimplyInspect Standalone Deployment Script

set -e

echo "======================================"
echo "SimplyInspect Standalone Deployment"
echo "======================================"
echo ""

# Check if .env.standalone file exists
if [ ! -f .env.standalone ]; then
    echo "Creating .env.standalone file from template..."
    cp .env.standalone .env
else
    cp .env.standalone .env
fi

# Check for required Azure credentials
source .env
if [ "$AZURE_TENANT_ID" == "your_tenant_id_here" ]; then
    echo "⚠️  WARNING: Azure credentials not configured!"
    echo "Please edit .env.standalone with your Azure AD credentials:"
    echo "  - AZURE_TENANT_ID"
    echo "  - AZURE_CLIENT_ID" 
    echo "  - AZURE_CLIENT_SECRET"
    echo "  - SHAREPOINT_URL"
    echo ""
    read -p "Do you want to continue with demo mode? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "🔧 Stopping any existing containers..."
docker-compose -f docker-compose.standalone.yml down

echo "🗑️  Cleaning up old containers and images..."
docker-compose -f docker-compose.standalone.yml rm -f

echo "🏗️  Building SimplyInspect containers..."
docker-compose -f docker-compose.standalone.yml build --no-cache

echo "🚀 Starting SimplyInspect..."
docker-compose -f docker-compose.standalone.yml up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker ps | grep -q simplyinspect-api; then
    echo "✅ API service is running"
else
    echo "❌ API service failed to start"
fi

if docker ps | grep -q simplyinspect-ui; then
    echo "✅ UI service is running"
else
    echo "❌ UI service failed to start"
fi

if docker ps | grep -q simplyinspect-db; then
    echo "✅ Database service is running"
else
    echo "❌ Database service failed to start"
fi

echo ""
echo "======================================"
echo "✨ SimplyInspect is now running!"
echo "======================================"
echo ""
echo "📊 Access Points:"
echo "  • Web UI: http://localhost:3001"
echo "  • API Docs: http://localhost:8001/docs"
echo "  • Database: localhost:5433 (user: simplyinspect)"
echo ""
echo "📝 Useful Commands:"
echo "  • View logs: docker-compose -f docker-compose.standalone.yml logs -f"
echo "  • Stop all: docker-compose -f docker-compose.standalone.yml down"
echo "  • Restart: docker-compose -f docker-compose.standalone.yml restart"
echo ""
echo "🔍 First Steps:"
echo "  1. Open http://localhost:3001 in your browser"
echo "  2. Navigate to SharePoint Permissions to analyze your SharePoint"
echo "  3. Go to Purview Audit Logs to sync audit data"
echo ""

# Show logs for debugging if needed
read -p "Do you want to see the logs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose -f docker-compose.standalone.yml logs --tail=50
fi