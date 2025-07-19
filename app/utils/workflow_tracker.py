"""
Workflow Tracker - Prevents multiple concurrent workflows for same contact
"""
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from app.utils.simple_logger import get_logger
import asyncio

logger = get_logger("workflow_tracker")


class WorkflowTracker:
    """
    Tracks active workflows to prevent duplicate processing.
    Uses in-memory tracking with TTL.
    """
    
    def __init__(self, ttl_seconds: int = 60):
        self.active_workflows: Dict[str, datetime] = {}  # contact_id -> start_time
        self.ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
    
    async def _cleanup_stale_workflows(self):
        """Remove workflows that have exceeded TTL"""
        now = datetime.now()
        expired = [
            contact_id for contact_id, start_time in self.active_workflows.items()
            if now - start_time > self.ttl
        ]
        for contact_id in expired:
            del self.active_workflows[contact_id]
            logger.warning(f"Cleaned up stale workflow for contact {contact_id}")
    
    async def start_workflow(self, contact_id: str) -> bool:
        """
        Try to start a workflow for a contact.
        
        Args:
            contact_id: The contact ID
            
        Returns:
            True if workflow can start (no active workflow), False if already active
        """
        async with self._lock:
            # Cleanup stale workflows
            await self._cleanup_stale_workflows()
            
            # Check if already active
            if contact_id in self.active_workflows:
                age = (datetime.now() - self.active_workflows[contact_id]).total_seconds()
                logger.warning(
                    f"Workflow already active for contact {contact_id} "
                    f"(started {age:.1f} seconds ago)"
                )
                return False
            
            # Mark as active
            self.active_workflows[contact_id] = datetime.now()
            logger.info(f"Started workflow for contact {contact_id}")
            return True
    
    async def end_workflow(self, contact_id: str):
        """Mark a workflow as completed"""
        async with self._lock:
            if contact_id in self.active_workflows:
                duration = (datetime.now() - self.active_workflows[contact_id]).total_seconds()
                del self.active_workflows[contact_id]
                logger.info(f"Ended workflow for contact {contact_id} (duration: {duration:.1f}s)")
            else:
                logger.warning(f"Tried to end non-existent workflow for contact {contact_id}")
    
    async def is_active(self, contact_id: str) -> bool:
        """Check if a workflow is currently active for a contact"""
        async with self._lock:
            await self._cleanup_stale_workflows()
            return contact_id in self.active_workflows
    
    def get_stats(self) -> Dict[str, int]:
        """Get workflow tracking statistics"""
        return {
            "active_workflows": len(self.active_workflows),
            "ttl_seconds": self.ttl.total_seconds()
        }


# Global instance
_tracker = WorkflowTracker()


async def can_start_workflow(contact_id: str) -> bool:
    """Check if we can start a workflow for this contact"""
    return await _tracker.start_workflow(contact_id)


async def end_workflow(contact_id: str):
    """Mark workflow as completed"""
    await _tracker.end_workflow(contact_id)


async def is_workflow_active(contact_id: str) -> bool:
    """Check if workflow is currently active"""
    return await _tracker.is_active(contact_id)


def get_workflow_stats() -> Dict[str, int]:
    """Get workflow tracking statistics"""
    return _tracker.get_stats()