"""
Redis-based checkpoint saver for LangGraph
Provides persistent state storage across distributed deployments
"""
import json
import os
from typing import Optional, Iterator, Any, Dict, Tuple, AsyncIterator
from contextlib import contextmanager
import redis.asyncio as redis
from redis.asyncio import Redis
from langgraph.checkpoint.base import (
    BaseCheckpointSaver, 
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from app.utils.simple_logger import get_logger
from app.utils.tracing import trace_operation

logger = get_logger("redis_store")


class RedisCheckpointSaver(BaseCheckpointSaver):
    """
    Redis-backed checkpoint saver for LangGraph state persistence.
    
    Features:
    - Persistent storage across process restarts
    - Distributed deployment support
    - Atomic operations
    - TTL support for automatic cleanup
    - Observability with tracing
    """
    
    def __init__(
        self, 
        redis_url: Optional[str] = None,
        key_prefix: str = "langgraph:checkpoint:",
        ttl_seconds: Optional[int] = 86400 * 7,  # 7 days default
        serde: Optional[JsonPlusSerializer] = None
    ):
        """
        Initialize Redis checkpoint saver.
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            key_prefix: Prefix for all checkpoint keys
            ttl_seconds: Time-to-live for checkpoints (None = no expiry)
            serde: Serializer for checkpoint data
        """
        super().__init__(serde=serde or JsonPlusSerializer())
        
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        self._client: Optional[Redis] = None
        
        logger.info(
            "Redis checkpoint saver initialized",
            redis_url=self.redis_url,
            key_prefix=key_prefix,
            ttl_seconds=ttl_seconds
        )
    
    async def _get_client(self) -> Redis:
        """Get or create Redis client"""
        if self._client is None:
            self._client = await redis.from_url(
                self.redis_url,
                decode_responses=False,  # We handle encoding
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 3,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 3,  # TCP_KEEPCNT
                }
            )
            # Test connection
            await self._client.ping()
            logger.info("Redis connection established")
        return self._client
    
    def _checkpoint_key(self, config: Dict[str, Any]) -> str:
        """Generate Redis key for checkpoint"""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id", "latest")
        
        if checkpoint_ns:
            return f"{self.key_prefix}{thread_id}:{checkpoint_ns}:{checkpoint_id}"
        return f"{self.key_prefix}{thread_id}:{checkpoint_id}"
    
    def _metadata_key(self, thread_id: str, checkpoint_ns: str = "") -> str:
        """Generate Redis key for checkpoint metadata list"""
        if checkpoint_ns:
            return f"{self.key_prefix}meta:{thread_id}:{checkpoint_ns}"
        return f"{self.key_prefix}meta:{thread_id}"
    
    @trace_operation("state.write")
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> Dict[str, Any]:
        """Save checkpoint to Redis"""
        client = await self._get_client()
        
        # Generate keys
        checkpoint_key = self._checkpoint_key(config)
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        metadata_key = self._metadata_key(thread_id, checkpoint_ns)
        
        # Prepare checkpoint data
        checkpoint_data = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "config": config,
            "parent_config": config.get("configurable", {}).get("checkpoint_id"),
        }
        
        # Serialize
        serialized = self.serde.dumps_typed(checkpoint_data)[1]
        
        # Measure state size for metrics
        state_size_bytes = len(serialized)
        logger.info(
            "Saving checkpoint to Redis",
            thread_id=thread_id,
            checkpoint_id=checkpoint["id"],
            size_bytes=state_size_bytes,
            channel_count=len(checkpoint.get("channel_values", {}))
        )
        
        # Save to Redis with optional TTL
        pipe = client.pipeline()
        
        # Store checkpoint
        if self.ttl_seconds:
            pipe.setex(checkpoint_key, self.ttl_seconds, serialized)
        else:
            pipe.set(checkpoint_key, serialized)
        
        # Update metadata list (for listing checkpoints)
        metadata_entry = {
            "checkpoint_id": checkpoint["id"],
            "parent_id": config.get("configurable", {}).get("checkpoint_id"),
            "metadata": metadata,
            "created_at": metadata.get("created_at", checkpoint["ts"]),
        }
        pipe.zadd(
            metadata_key,
            {json.dumps(metadata_entry): checkpoint["ts"]}
        )
        
        # Trim metadata list to keep only recent entries
        pipe.zremrangebyrank(metadata_key, 0, -101)  # Keep last 100
        
        await pipe.execute()
        
        # Return updated config
        return {
            **config,
            "configurable": {
                **config["configurable"],
                "checkpoint_id": checkpoint["id"],
            }
        }
    
    @trace_operation("state.read")
    async def aget(
        self,
        config: Dict[str, Any]
    ) -> Optional[CheckpointTuple]:
        """Load checkpoint from Redis"""
        client = await self._get_client()
        
        checkpoint_key = self._checkpoint_key(config)
        thread_id = config["configurable"]["thread_id"]
        
        logger.info(
            "Loading checkpoint from Redis",
            thread_id=thread_id,
            checkpoint_key=checkpoint_key
        )
        
        # Get checkpoint data
        data = await client.get(checkpoint_key)
        if not data:
            logger.info("No checkpoint found", thread_id=thread_id)
            return None
        
        # Deserialize
        checkpoint_data = self.serde.loads_typed((b"msgpack", data))
        
        # Extract components
        checkpoint = checkpoint_data["checkpoint"]
        metadata = checkpoint_data["metadata"]
        parent_config = checkpoint_data.get("parent_config")
        
        # Build parent config if exists
        if parent_config:
            parent_config = {
                **config,
                "configurable": {
                    **config["configurable"],
                    "checkpoint_id": parent_config,
                }
            }
        
        logger.info(
            "Checkpoint loaded from Redis",
            thread_id=thread_id,
            checkpoint_id=checkpoint["id"],
            message_count=len(checkpoint.get("channel_values", {}).get("messages", [])),
            parent_exists=parent_config is not None
        )
        
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=[]
        )
    
    async def alist(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints from Redis"""
        client = await self._get_client()
        
        # Get thread_id from config
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        metadata_key = self._metadata_key(thread_id, checkpoint_ns)
        
        # Get metadata list (sorted by timestamp)
        entries = await client.zrevrange(metadata_key, 0, limit or 10, withscores=True)
        
        for entry_json, score in entries:
            entry = json.loads(entry_json)
            
            # Apply filters if provided
            if filter:
                if not all(entry["metadata"].get(k) == v for k, v in filter.items()):
                    continue
            
            # Build config for this checkpoint
            checkpoint_config = {
                **config,
                "configurable": {
                    **config["configurable"],
                    "checkpoint_id": entry["checkpoint_id"],
                }
            }
            
            # Load full checkpoint
            checkpoint_tuple = await self.aget(checkpoint_config)
            if checkpoint_tuple:
                yield checkpoint_tuple
    
    def list(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """Sync list not implemented - use alist"""
        raise NotImplementedError("Use alist for async operations")
    
    def get(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Sync get not implemented - use aget"""
        raise NotImplementedError("Use aget for async operations")
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> Dict[str, Any]:
        """Sync put not implemented - use aput"""
        raise NotImplementedError("Use aput for async operations")
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Sync get_tuple not implemented - use aget"""
        raise NotImplementedError("Use aget for async operations")
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        if self._client:
            # Schedule cleanup but don't block
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.create_task(self.close())
            except RuntimeError:
                pass


@contextmanager
def get_redis_checkpointer(**kwargs) -> RedisCheckpointSaver:
    """
    Context manager for Redis checkpointer.
    
    Usage:
        with get_redis_checkpointer() as checkpointer:
            workflow = graph.compile(checkpointer=checkpointer)
    """
    checkpointer = RedisCheckpointSaver(**kwargs)
    try:
        yield checkpointer
    finally:
        # Cleanup handled by __del__
        pass