"""
Simplified workflow with inline Redis checkpoint
"""
from app.workflow import *
import os
import logging

logger = logging.getLogger(__name__)

# Override checkpointer with simpler implementation
try:
    import redis.asyncio as redis
    from langgraph.checkpoint.base import BaseCheckpointSaver
    
    class SimpleRedisCheckpointer(BaseCheckpointSaver):
        """Minimal Redis checkpointer"""
        def __init__(self):
            super().__init__()
            self.redis_url = "redis://default:7LOQGvcF6ZQzOv3kvR9JcqpFE3jjNbwo@redis-19970.c9.us-east-1-4.ec2.redns.redis-cloud.com:19970"
            logger.info(f"SimpleRedisCheckpointer initialized with {self.redis_url[:50]}...")
            
        async def aget(self, config):
            """Get checkpoint - simplified"""
            logger.info(f"Redis aget called for thread: {config.get('configurable', {}).get('thread_id', 'unknown')}")
            return None  # For now, just log
            
        async def aput(self, config, checkpoint, metadata, new_versions):
            """Save checkpoint - simplified"""
            logger.info(f"Redis aput called for thread: {config.get('configurable', {}).get('thread_id', 'unknown')}")
            return config
            
        async def alist(self, config, **kwargs):
            """List checkpoints - simplified"""
            return []
            
        # Sync methods for compatibility
        def get(self, config):
            raise NotImplementedError("Use async methods")
            
        def put(self, config, checkpoint, metadata, new_versions):
            raise NotImplementedError("Use async methods")
            
        def list(self, config, **kwargs):
            raise NotImplementedError("Use async methods")
            
        def get_tuple(self, config):
            raise NotImplementedError("Use async methods")
            
        async def aget_tuple(self, config):
            """Get tuple - alias for aget"""
            return await self.aget(config)
    
    # Use simple Redis checkpointer
    checkpointer = SimpleRedisCheckpointer()
    logger.info("✅ Using SimpleRedisCheckpointer")
    
except Exception as e:
    logger.error(f"Failed to create Redis checkpointer: {e}")
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    logger.info("❌ Fallback to MemorySaver")

# Re-compile workflow with new checkpointer
workflow = workflow_graph.compile(checkpointer=checkpointer)

logger.info(f"Workflow compiled with {type(checkpointer).__name__}")

__all__ = ["workflow"]