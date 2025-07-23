"""
Production Workflow with Hardcoded Redis URL for Testing
Temporary workaround to ensure Redis is used
"""
from app.workflow import *  # Import everything from the fixed workflow
import os

# Override the create_checkpointer function
def create_checkpointer_hardcoded():
    """Create checkpointer with hardcoded Redis URL"""
    # TEMPORARY: Hardcode Redis URL for testing
    redis_url = "redis://default:7LOQGvcF6ZQzOv3kvR9JcqpFE3jjNbwo@redis-19970.c9.us-east-1-4.ec2.redns.redis-cloud.com:19970"
    
    try:
        from app.state.redis_store import RedisCheckpointSaver
        logger.info(f"FORCING Redis checkpointer with URL: {redis_url[:50]}...")
        return RedisCheckpointSaver(redis_url=redis_url)
    except Exception as e:
        logger.error(f"Failed to create Redis checkpointer: {e}")
        # Still fallback to memory if Redis fails
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

# Re-create checkpointer with hardcoded URL
checkpointer = create_checkpointer_hardcoded()

# Re-compile workflow with forced Redis
workflow = workflow_graph.compile(checkpointer=checkpointer)

logger.info(f"Production workflow compiled with FORCED {type(checkpointer).__name__}")

# Export
__all__ = ["workflow"]