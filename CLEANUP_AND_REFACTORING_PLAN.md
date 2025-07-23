# LangGraph GHL Agent - Cleanup and Refactoring Plan

## Overview
This plan outlines a systematic approach to clean up the codebase and refactor for better maintainability, performance, and reliability.

## Phase 1: Immediate Cleanup (1-2 days)

### 1.1 Remove Dead Code
```bash
# Files to delete
rm app/agents/supervisor_obsolete.py.bak
rm app/agents/responder_agent_old.py
rm app/tools/ghl_client_old.py
rm app/tools/ghl_streaming.py  # If confirmed unused
```

### 1.2 Fix Critical Bugs
- [ ] Fix string formatting in `/api/webhook_ghl_fixed.py:146`
- [ ] Remove import of non-existent `ghl_client_simple.py`

### 1.3 Consolidate Webhook Handlers
- [ ] Determine which webhook handler is used in production
- [ ] Merge features from both into single handler
- [ ] Archive the unused version

## Phase 2: Code Organization (3-5 days)

### 2.1 Standardize Project Structure
```
langgraph-ghl-agent/
├── app/
│   ├── agents/          # Keep agent implementations
│   ├── tools/           # Keep tool implementations
│   ├── core/            # NEW: Core business logic
│   │   ├── state.py     # Consolidated state definitions
│   │   ├── routing.py   # Routing logic
│   │   └── config.py    # Centralized configuration
│   ├── api/             # API endpoints
│   ├── utils/           # Utilities
│   └── workflow.py      # Main workflow definition
├── tests/               # Comprehensive tests
├── docs/                # Documentation
└── scripts/             # Deployment and utility scripts
```

### 2.2 Consolidate State Management
Create a single source of truth for state:

```python
# app/core/state.py
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class ConversationState(TypedDict):
    """Core conversation state - only required fields"""
    messages: List[BaseMessage]
    contact_id: str
    conversation_id: str
    thread_id: str
    
class AgentState(ConversationState):
    """Extended state for agent operations"""
    current_agent: str
    next_agent: Optional[str]
    lead_score: int
    routing_complete: bool
    
class ProductionState(AgentState):
    """Full production state with all fields"""
    # Add remaining fields as needed
```

### 2.3 Simplify Configuration
```python
# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    ghl_api_token: str
    ghl_location_id: str
    langgraph_url: str = "http://localhost:2024"
    
    # Business Configuration
    company_name: str = "AI Solutions"
    service_type: str = "automation"
    
    # GHL Custom Field IDs
    lead_score_field_id: str = "wAPjuqxtfgKLCJqahjo1"
    business_type_field_id: str = "HtoheVc48qvAfvRUKhfG"
    last_intent_field_id: str = "Q1n5kaciimUU6JN5PBD6"
    
    class Config:
        env_file = ".env"
```

## Phase 3: Core Refactoring (1 week)

### 3.1 Create Abstract Base Agent
```python
# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str, score_range: tuple):
        self.name = name
        self.min_score, self.max_score = score_range
        
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the conversation state"""
        pass
        
    def can_handle(self, score: int) -> bool:
        """Check if this agent can handle the given score"""
        return self.min_score <= score <= self.max_score
```

### 3.2 Implement Consistent Error Handling
```python
# app/core/exceptions.py
class GHLAgentError(Exception):
    """Base exception for all agent errors"""
    pass

class GHLAPIError(GHLAgentError):
    """GHL API related errors"""
    pass

class RoutingError(GHLAgentError):
    """Routing related errors"""
    pass

# app/utils/error_handler.py
from functools import wraps
import logging

def handle_agent_errors(logger: logging.Logger):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except GHLAPIError as e:
                logger.error(f"GHL API Error: {e}")
                return {"error": "API error occurred", "details": str(e)}
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                return {"error": "Internal error", "details": str(e)}
        return wrapper
    return decorator
```

### 3.3 Implement Proper Logging
```python
# app/core/logging.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    """Structured logging for better observability"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def log_event(self, event: str, **kwargs):
        """Log structured event"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))
```

## Phase 4: Testing Strategy (1 week)

### 4.1 Unit Tests
```python
# tests/test_agents/test_maria.py
import pytest
from app.agents.maria_agent import MariaAgent

@pytest.mark.asyncio
async def test_maria_handles_low_scores():
    agent = MariaAgent()
    state = {"lead_score": 3, "messages": [...]}
    result = await agent.process(state)
    assert result["current_agent"] == "maria"
    assert not result.get("needs_escalation")
```

### 4.2 Integration Tests
```python
# tests/test_workflow.py
@pytest.mark.asyncio
async def test_full_conversation_flow():
    """Test complete conversation from webhook to response"""
    # Test webhook → mapper → receptionist → router → agent → responder
```

### 4.3 Load Tests
```python
# tests/load/test_concurrent_conversations.py
async def test_handle_multiple_conversations():
    """Ensure system handles concurrent conversations"""
```

## Phase 5: Performance Optimization (3-5 days)

### 5.1 Implement Caching
```python
# app/core/cache.py
from functools import lru_cache
import asyncio

class ConversationCache:
    """Cache for conversation data"""
    
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
        
    async def get_or_load(self, key: str, loader_func):
        if key in self.cache:
            return self.cache[key]
        value = await loader_func()
        self.cache[key] = value
        # Schedule cleanup
        asyncio.create_task(self._cleanup(key))
        return value
```

### 5.2 Connection Pooling
```python
# app/core/http_client.py
import httpx

class HTTPClientPool:
    """Managed HTTP client pool"""
    
    def __init__(self, max_connections: int = 10):
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=max_connections)
        )
```

## Phase 6: Documentation (Ongoing)

### 6.1 API Documentation
- Document all webhook endpoints
- Document expected request/response formats
- Create OpenAPI/Swagger spec

### 6.2 Agent Documentation
- Document each agent's purpose and behavior
- Document state transitions
- Create decision flow diagrams

### 6.3 Deployment Documentation
- Environment setup guide
- Configuration reference
- Troubleshooting guide

## Implementation Timeline

| Week | Phase | Tasks |
|------|-------|-------|
| 1 | Phase 1-2 | Immediate cleanup, fix bugs, organize code |
| 2 | Phase 3 | Core refactoring, base classes, error handling |
| 3 | Phase 4 | Implement comprehensive testing |
| 4 | Phase 5-6 | Performance optimization, documentation |

## Success Metrics

1. **Code Quality**
   - 0 critical bugs
   - 80%+ test coverage
   - All linting checks pass

2. **Performance**
   - < 500ms average response time
   - Support 100+ concurrent conversations
   - < 1% error rate

3. **Maintainability**
   - Clear separation of concerns
   - Consistent patterns throughout
   - Comprehensive documentation

## Risk Mitigation

1. **Backward Compatibility**
   - Maintain existing API contracts
   - Phase rollout with feature flags
   - Keep backup of current version

2. **Testing in Production**
   - Use canary deployments
   - Monitor error rates closely
   - Have rollback plan ready

3. **Team Coordination**
   - Daily standup during refactoring
   - Code reviews for all changes
   - Document all decisions

## Next Steps

1. Get team buy-in on this plan
2. Set up proper development environment
3. Create feature branches for each phase
4. Begin with Phase 1 immediate cleanup

This refactoring will transform the codebase from a working prototype to a production-ready system that's maintainable, scalable, and reliable.