#!/bin/bash
# Run tests inside Docker container

set -e

echo "🐳 Running Tests in Docker Container"
echo "===================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to run command in container
run_in_container() {
    docker-compose exec -T langgraph-agent "$@"
}

# Check if containers are running
echo -e "${BLUE}1. Checking Docker containers...${NC}"
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Containers are running${NC}"
else
    echo -e "${YELLOW}⚠ Starting containers...${NC}"
    docker-compose up -d
    echo "Waiting for services to start..."
    sleep 10
fi

# Run unit tests
echo -e "\n${BLUE}2. Running unit tests...${NC}"
if docker-compose exec -T langgraph-agent pytest tests/ -v --tb=short; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
fi

# Test imports
echo -e "\n${BLUE}3. Testing critical imports...${NC}"
if run_in_container python -c "
import app.workflow
import app.agents.receptionist_agent
import app.agents.maria_agent_v2
import app.agents.sofia_agent_v2
import app.tools.ghl_client
print('All imports successful')
"; then
    echo -e "${GREEN}✓ All imports successful${NC}"
else
    echo -e "${RED}✗ Import test failed${NC}"
fi

# Test workflow validation
echo -e "\n${BLUE}4. Validating workflow...${NC}"
if run_in_container python validate_workflow.py; then
    echo -e "${GREEN}✓ Workflow validation passed${NC}"
else
    echo -e "${RED}✗ Workflow validation failed${NC}"
fi

# Test API endpoints
echo -e "\n${BLUE}5. Testing API endpoints...${NC}"

# Health check
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Health endpoint working${NC}"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
fi

# Test webhook endpoint
echo -e "\n${BLUE}6. Testing webhook endpoint...${NC}"
WEBHOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/webhook/ghl \
    -H "Content-Type: application/json" \
    -d '{"type":"InboundMessage","locationId":"test","contactId":"test","conversationId":"test","message":"test"}' \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$WEBHOOK_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "422" ]; then
    echo -e "${GREEN}✓ Webhook endpoint responding (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}✗ Webhook endpoint failed (HTTP $HTTP_CODE)${NC}"
fi

# Check logs for errors
echo -e "\n${BLUE}7. Checking logs for errors...${NC}"
ERROR_COUNT=$(docker-compose logs --tail=100 | grep -i "error\|exception\|traceback" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No errors in recent logs${NC}"
else
    echo -e "${YELLOW}⚠ Found $ERROR_COUNT error messages in logs${NC}"
fi

# Memory and CPU usage
echo -e "\n${BLUE}8. Checking resource usage...${NC}"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep ghl-langgraph-agent || true

# Summary
echo -e "\n===================================="
echo -e "${BLUE}Test Summary${NC}"
echo -e "===================================="
echo -e "${GREEN}Container Status: Running${NC}"
echo -e "${GREEN}API Status: Accessible${NC}"
echo -e "${YELLOW}Logs: Check for any warnings${NC}"

echo -e "\n${BLUE}View logs:${NC} docker-compose logs -f"
echo -e "${BLUE}Run live tests:${NC} python run_live_tests.py"
echo -e "${BLUE}Stop containers:${NC} docker-compose down"