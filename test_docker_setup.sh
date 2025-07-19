#!/bin/bash
# Docker Setup Test Script for LangGraph GHL Agent

set -e  # Exit on error

echo "🐳 Docker Setup Test Script"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ "$1" = "success" ]; then
        echo -e "${GREEN}✓ $2${NC}"
    elif [ "$1" = "error" ]; then
        echo -e "${RED}✗ $2${NC}"
    elif [ "$1" = "warning" ]; then
        echo -e "${YELLOW}⚠ $2${NC}"
    else
        echo "$2"
    fi
}

# Check Docker is installed
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_status "success" "Docker is installed: $(docker --version)"
else
    print_status "error" "Docker is not installed"
    exit 1
fi

# Check Docker Compose is installed
echo -e "\n2. Checking Docker Compose installation..."
if command -v docker-compose &> /dev/null; then
    print_status "success" "Docker Compose is installed: $(docker-compose --version)"
elif docker compose version &> /dev/null; then
    print_status "success" "Docker Compose V2 is installed: $(docker compose version)"
else
    print_status "error" "Docker Compose is not installed"
    exit 1
fi

# Check if Docker daemon is running
echo -e "\n3. Checking Docker daemon..."
if docker info &> /dev/null; then
    print_status "success" "Docker daemon is running"
else
    print_status "error" "Docker daemon is not running"
    exit 1
fi

# Check if .env file exists
echo -e "\n4. Checking environment configuration..."
if [ -f .env ]; then
    print_status "success" ".env file exists"
    
    # Check required environment variables
    required_vars=("GHL_API_TOKEN" "GHL_LOCATION_ID" "OPENAI_API_KEY" "SUPABASE_URL" "SUPABASE_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=.*-here$" .env; then
            print_status "success" "$var is configured"
        else
            missing_vars+=("$var")
            print_status "warning" "$var needs to be configured"
        fi
    done
    
    if [ ${#missing_vars[@]} -eq 0 ]; then
        print_status "success" "All required environment variables are configured"
    else
        print_status "warning" "${#missing_vars[@]} environment variables need configuration"
    fi
else
    print_status "error" ".env file not found"
    print_status "info" "Creating .env from .env.example..."
    cp .env.example .env
    print_status "warning" "Please configure your .env file before running Docker"
fi

# Build Docker image
echo -e "\n5. Building Docker image..."
if docker build -t ghl-langgraph-agent:test . ; then
    print_status "success" "Docker image built successfully"
else
    print_status "error" "Failed to build Docker image"
    exit 1
fi

# Check Docker Compose configuration
echo -e "\n6. Validating Docker Compose configuration..."
if docker-compose config &> /dev/null || docker compose config &> /dev/null; then
    print_status "success" "Docker Compose configuration is valid"
else
    print_status "error" "Docker Compose configuration is invalid"
    exit 1
fi

# Test container startup (dry run)
echo -e "\n7. Testing container startup (dry run)..."
if docker run --rm -e PORT=8000 ghl-langgraph-agent:test python -c "print('Container starts successfully')" ; then
    print_status "success" "Container can start successfully"
else
    print_status "error" "Container failed to start"
    exit 1
fi

# Check port availability
echo -e "\n8. Checking port availability..."
if lsof -i:8000 &> /dev/null; then
    print_status "warning" "Port 8000 is already in use"
else
    print_status "success" "Port 8000 is available"
fi

# Summary
echo -e "\n=========================="
echo "📊 Docker Setup Summary"
echo "=========================="
print_status "success" "Docker environment is ready for testing"
echo -e "\nNext steps:"
echo "1. Configure your .env file with actual values"
echo "2. Run: docker-compose up -d"
echo "3. Check logs: docker-compose logs -f"
echo "4. Test webhook: curl http://localhost:8000/health"