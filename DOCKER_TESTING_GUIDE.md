# Docker Testing Guide for LangGraph GHL Agent

This guide explains how to test the LangGraph GHL Agent using Docker.

## Prerequisites

- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)
- `.env` file configured with your API keys

## Quick Start

```bash
# 1. Test Docker setup
make docker-test

# 2. Start containers
make docker-up

# 3. Run live tests
make live-test

# 4. View logs
make docker-logs
```

## Available Testing Commands

### Docker Setup Testing

```bash
# Test Docker environment and configuration
./test_docker_setup.sh
# or
make docker-test
```

This will check:
- Docker and Docker Compose installation
- Docker daemon status
- Environment configuration
- Port availability
- Build the Docker image
- Validate docker-compose.yml

### Container Management

```bash
# Start containers
make docker-up

# Stop containers
make docker-down

# View logs
make docker-logs

# Build/rebuild image
make docker-build
```

### Running Tests

#### 1. Test Inside Docker Container

```bash
# Run all tests inside the container
./test_in_docker.sh
# or
make test-docker
```

This runs:
- Unit tests with pytest
- Import validation
- Workflow validation
- API endpoint tests
- Log error checking
- Resource usage monitoring

#### 2. Live Integration Tests

```bash
# Run comprehensive live tests against running service
python run_live_tests.py
# or
make live-test
```

This tests:
- Health endpoint
- Webhook validation
- Receptionist flow
- Qualification flow (Maria)
- Appointment flow (Sofia)
- Conversation history
- Concurrent request handling

## Environment Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Configure required variables:
```
GHL_API_TOKEN=your-token
GHL_LOCATION_ID=your-location-id
OPENAI_API_KEY=your-openai-key
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

## Testing Workflow

### 1. Local Development Testing

```bash
# Validate workflow
make validate

# Run unit tests
make test

# Start locally
make run
```

### 2. Docker Testing

```bash
# Test Docker setup
make docker-test

# Build and start containers
make docker-build
make docker-up

# Run tests in container
make test-docker

# Run live integration tests
make live-test

# Check logs for issues
make docker-logs
```

### 3. Production-like Testing

```bash
# Start with production config
docker-compose -f docker-compose.yml up -d

# Monitor health
curl http://localhost:8000/health

# Test webhook endpoint
curl -X POST http://localhost:8000/webhook/ghl \
  -H "Content-Type: application/json" \
  -d '{
    "type": "InboundMessage",
    "locationId": "test-location",
    "contactId": "test-contact",
    "conversationId": "test-conversation",
    "message": "Hola, necesito información"
  }'
```

## Debugging

### View Container Logs

```bash
# All logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Specific service
docker-compose logs langgraph-agent

# Last 100 lines
docker-compose logs --tail=100
```

### Access Container Shell

```bash
# Enter container
docker-compose exec langgraph-agent bash

# Run Python shell
docker-compose exec langgraph-agent python

# Run specific command
docker-compose exec langgraph-agent pytest tests/
```

### Check Container Status

```bash
# List containers
docker-compose ps

# Check resource usage
docker stats

# Inspect container
docker inspect ghl-langgraph-agent
```

## Common Issues

### Port Already in Use

```bash
# Find process using port 8000
lsof -i:8000

# Kill process
kill -9 <PID>
```

### Container Won't Start

```bash
# Check logs
docker-compose logs langgraph-agent

# Rebuild image
docker-compose build --no-cache

# Remove all and restart
docker-compose down -v
docker-compose up -d
```

### Tests Failing

1. Check environment variables in `.env`
2. Ensure all services are running: `docker-compose ps`
3. Check logs for errors: `docker-compose logs`
4. Verify API keys are valid
5. Check network connectivity

## Performance Testing

### Load Testing

```bash
# Install hey (HTTP load generator)
brew install hey  # macOS
# or
apt-get install hey  # Linux

# Test with 100 requests, 10 concurrent
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"type":"InboundMessage","message":"test"}' \
  http://localhost:8000/webhook/ghl
```

### Memory Profiling

```bash
# Monitor memory usage
docker stats ghl-langgraph-agent

# Check container limits
docker inspect ghl-langgraph-agent | grep -i memory
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Build Docker image
        run: docker build -t ghl-langgraph-agent:test .
      
      - name: Run Docker tests
        run: |
          docker-compose up -d
          sleep 10
          ./test_in_docker.sh
          docker-compose down
```

## Next Steps

1. Set up monitoring with LangSmith
2. Configure alerts for errors
3. Implement automated deployment
4. Add performance benchmarks
5. Set up staging environment