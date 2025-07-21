# GoHighLevel LangGraph Messaging Agent (Enhanced v2)

A cutting-edge Python-based LangGraph implementation of the GoHighLevel messaging agent with intelligent lead routing, real-time streaming, parallel processing, and advanced error recovery.

## Overview

This enhanced system provides enterprise-grade features using LangGraph v0.5.3:

- **Real-time streaming responses** for instant user feedback
- **Parallel qualification checks** for 3x faster lead scoring
- **Intelligent message batching** for human-like conversations
- **Automatic context management** with token optimization
- **Advanced error recovery** with circuit breakers and retries
- **State persistence** with checkpointing and recovery
- **Production-ready** with comprehensive monitoring

## Architecture

### Core Components

1. **State Management** (`app/state/`)
   - Centralized conversation state
   - Lead information tracking
   - Message history management

2. **Enhanced Agents** (`app/agents/`)
   - **Maria**: Cold lead agent (Score 1-4) with error recovery
   - **Carlos**: Warm lead agent (Score 5-7) with parallel qualification
   - **Sofia**: Hot lead agent (Score 8-10) with streaming responses

3. **Tools** (`app/tools/`)
   - GoHighLevel API integration
   - Appointment booking
   - Calendar availability checking
   - Contact management

4. **Enhanced Workflow** (`app/workflow_v2.py`)
   - LangGraph StateGraph with supervisor pattern
   - Intelligence layer for pre-processing
   - Command-based routing with error protection
   - Streaming support for real-time responses
   - Performance metrics and monitoring

## Setup

### Prerequisites

- Python 3.13+ (required for deployment - includes free-threading and JIT)
- pip
- Virtual environment (recommended)
- Redis (optional, for distributed message batching)
- LangSmith API key (recommended for monitoring)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd langgraph-ghl-agent
```

2. Create and activate virtual environment:
```bash
python3.13 -m venv venv313
source venv313/bin/activate  # On Windows: venv313\Scripts\activate
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

## Quick Start (Enhanced)

### Using All Enhanced Features

```bash
# Start with enhanced features
python start_enhanced.py
```

This will:
- Enable streaming responses ✅
- Enable parallel qualification ✅
- Enable message batching ✅
- Enable error recovery ✅
- Start enhanced webhook server ✅

## API Endpoints

### Standard Endpoints
- `POST /webhook/message` - Main webhook endpoint with batching
- `GET /` - Basic health check
- `GET /health` - Detailed health check with component status

### Enhanced Endpoints
- `POST /webhook/message/stream` - Streaming webhook for real-time responses
- `POST /webhook/appointment` - Appointment webhook with streaming confirmation

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

### Recommended Deployment Platform

#### LangGraph Platform (LangSmith) - RECOMMENDED
Best for: Native LangGraph support, built-in monitoring, automatic scaling

```bash
# Deploy to LangGraph Platform
# Automatic deployment on push to main branch
git push origin main
```

Features:
- Automatic deployment on git push
- Built-in LangSmith monitoring
- Native LangGraph optimizations
- Automatic retries and error handling
- Streaming support out of the box
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
