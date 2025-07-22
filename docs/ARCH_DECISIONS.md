# Architecture Decisions

## Repository Layout

```
langgraph-ghl-agent/
├── src/                    # LangGraph Platform exports
│   ├── graph.py           # Exports workflow for agent graph
│   └── webapp.py          # Exports FastAPI app for HTTP
├── app/                   # Core application logic
│   ├── workflow.py        # Main LangGraph workflow definition
│   ├── agents/            # Individual agent implementations
│   ├── state/             # State definitions (MinimalState)
│   └── api/               # FastAPI webhook handlers
└── langgraph.json         # Platform configuration
```

## State Model

```python
class MinimalState(TypedDict):
    messages: Annotated[List[str], add_messages]
    contact_id: str
    conversation_id: str
    location_id: str
    contact_info: ContactInfo  # Score, name, phone, email
    next: str                  # Next agent routing
```

Key decisions:
- Minimal state to reduce memory overhead
- SQLite checkpointing for conversation persistence
- Thread ID = conversation ID for continuity

## Webhook to Graph Flow

1. **Webhook Receipt** → `/webhooks/chat/inbound`
2. **Message Processing** → Extract GHL payload
3. **Intelligence Analysis** → Score lead (1-10)
4. **Graph Invocation**:
   ```python
   thread_id = f"ghl-{conversation_id}"
   result = workflow.invoke(
       {"messages": [message], ...},
       {"configurable": {"thread_id": thread_id}}
   )
   ```
5. **Response Streaming** → Back to GHL API

## Known TODOs & Risks

### Critical
- **Supabase Dependency**: Optional but not cleanly abstracted
- **Error Recovery**: No retry mechanism for GHL API failures
- **Rate Limiting**: No protection against webhook floods

### Important
- **Test Coverage**: Currently <50%, target is 70%
- **Type Safety**: Many `Any` types need proper annotations
- **Monitoring**: LangSmith integration needs documentation

### Nice to Have
- **Performance**: Consider Redis for high-volume deployments
- **Security**: Add webhook signature verification
- **Observability**: Structured logging with correlation IDs