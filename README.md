# GoHighLevel LangGraph Messaging Agent

A Python-based LangGraph implementation of the GoHighLevel messaging agent with intelligent lead routing and appointment booking capabilities.

## Overview

This system replaces the Node.js/JavaScript implementation with a more robust Python/LangGraph architecture that provides:

- State management with persistence
- Visual workflow debugging
- Checkpointing and recovery
- Better error handling
- Production-ready infrastructure

## Architecture

### Core Components

1. **State Management** (`app/state/`)
   - Centralized conversation state
   - Lead information tracking
   - Message history management

2. **Agents** (`app/agents/`)
   - Maria: Cold lead agent (Score 1-4)
   - Carlos: Warm lead agent (Score 5-7)
   - Sofia: Hot lead agent (Score 8-10)

3. **Tools** (`app/tools/`)
   - GoHighLevel API integration
   - Appointment booking
   - Calendar availability checking
   - Contact management

4. **Workflow** (`app/workflow.py`)
   - LangGraph StateGraph implementation
   - Conditional routing based on lead score
   - Agent handoff logic

## Setup

### Prerequisites

- Python 3.9+
- pip
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd langgraph-ghl-agent
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Running the Application

### Development Mode
```bash
python main.py
# Or with uvicorn directly:
uvicorn app.api.webhook:app --reload --port 8000
```

### Production Mode
```bash
gunicorn app.api.webhook:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Background Worker
```bash
# Run message queue processor
python worker.py
```

## API Endpoints

- `POST /webhook/message` - Main webhook endpoint for GoHighLevel messages
- `POST /webhook/appointment` - Webhook for appointment updates
- `GET /` - Basic health check
- `GET /health` - Detailed health check with service status

## Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

## Deployment

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t ghl-langgraph-agent .
docker run -p 8000:8000 --env-file .env ghl-langgraph-agent
```

### Recommended Deployment Platforms

#### 1. Render (Recommended)
Best for: Long-running processes, background workers, affordable pricing

```bash
# Deploy using render.yaml
render deploy
```

#### 2. Google Cloud Run
Best for: Enterprise scale, auto-scaling, longer timeouts

```bash
# Deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

#### 3. Fly.io
Best for: Global distribution, WebSocket support

```bash
# Deploy with Fly
fly launch
fly deploy
```

### Why Not Vercel or Railway?

- **Vercel**: Limited to 60-second timeouts, no background tasks, serverless only
- **Railway**: Better but still limited for long-running processes

LangGraph agents need:
- Long-running process support
- Background task processing
- Persistent connections
- State management

These requirements make traditional application platforms more suitable than serverless platforms.

## Migration Notes

This is a complete rewrite of the Node.js/Vercel implementation with the following improvements:

1. **Better State Management**: LangGraph provides built-in state persistence
2. **Visual Debugging**: Use LangGraph Studio to debug workflows
3. **Error Recovery**: Automatic checkpointing and recovery
4. **Type Safety**: Full Python type hints throughout
5. **Testing**: Comprehensive test suite with pytest

## License

Proprietary - All rights reserved# Force rebuild Thu Jul 17 21:57:27 CDT 2025
