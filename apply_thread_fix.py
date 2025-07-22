#!/usr/bin/env python3
"""
Apply the thread_id fix to app/workflow.py
This script shows exactly what needs to be changed
"""

# REQUIRED CHANGES TO app/workflow.py:

# 1. IMPORTS - Add these at the top
"""
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import os
from datetime import datetime
"""

# 2. REPLACE create_modernized_workflow() function:
"""
async def create_modernized_workflow():
    '''Create the workflow with SQLite persistence'''
    workflow_graph = ... # your existing graph creation
    
    # CRITICAL: Use SQLite for persistence across webhook calls
    checkpoint_db = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    
    # Create async SQLite checkpointer
    checkpointer = AsyncSqliteSaver.from_conn_string(checkpoint_db)
    store = InMemoryStore()
    
    compiled = workflow_graph.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info(f"Using SQLite checkpoint database: {checkpoint_db}")
    
    return compiled, checkpointer, checkpoint_db
"""

# 3. REPLACE run_workflow() function with this EXACT code:
def get_fixed_run_workflow():
    return '''
async def run_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the workflow with FIXED checkpoint loading
    """
    global _workflow, _checkpointer, _db_path
    
    try:
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        conversation_id = webhook_data.get("conversationId")
        
        # CRITICAL FIX: Always use contact-based thread_id for consistency
        thread_id = f"contact-{contact_id}"
        logger.info(f"🔧 THREAD FIX: Using thread_id: {thread_id} for contact: {contact_id}")
        
        # Configuration for checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        
        # Create workflow if not exists
        if _workflow is None:
            _workflow, _checkpointer, _db_path = await create_modernized_workflow()
            logger.info(f"Created workflow with SQLite at: {_db_path}")
        
        # Try to load existing checkpoint
        existing_messages = []
        existing_data = {}
        
        try:
            checkpoint_tuple = await _checkpointer.aget(config)
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                checkpoint_state = checkpoint_tuple.checkpoint.get("channel_values", {})
                existing_messages = checkpoint_state.get("messages", [])
                existing_data = checkpoint_state.get("extracted_data", {})
                
                logger.info(f"✅ Loaded checkpoint: {len(existing_messages)} previous messages")
                if existing_messages:
                    logger.info(f"   Last message: {existing_messages[-1].content[:50]}...")
                if existing_data:
                    logger.info(f"   Existing data: {existing_data}")
        except Exception as e:
            logger.warning(f"No checkpoint found for {thread_id}: {e}")
        
        # Build initial state
        initial_state = {
            "messages": existing_messages + [
                HumanMessage(
                    content=message_body,
                    additional_kwargs={
                        "contact_id": contact_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            ] if message_body else existing_messages,
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "contact_name": webhook_data.get("contact_name", ""),
            "contact_email": webhook_data.get("contact_email", ""),
            "contact_phone": webhook_data.get("contact_phone", ""),
            "location_id": webhook_data.get("locationId", ""),
            "conversation_id": conversation_id,
            "extracted_data": existing_data,  # Preserve extracted data
            "message_count": len(existing_messages) + 1
        }
        
        # Run workflow
        logger.info(f"Running workflow for message #{initial_state['message_count']}")
        result = await _workflow.ainvoke(
            initial_state,
            config=config  # Pass config for checkpoint saving
        )
        
        logger.info(f"✅ Workflow completed and saved to thread: {thread_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}", exc_info=True)
        raise
'''

# 4. ADD to requirements.txt:
"""
langgraph-checkpoint-sqlite>=2.0.10
aiosqlite>=0.19.0
"""

def print_instructions():
    """Print clear instructions for applying the fix"""
    print("=" * 70)
    print("INSTRUCTIONS TO FIX THREAD_ID ISSUE")
    print("=" * 70)
    
    print("\n1️⃣  UPDATE requirements.txt - Add these lines:")
    print("-" * 40)
    print("langgraph-checkpoint-sqlite>=2.0.10")
    print("aiosqlite>=0.19.0")
    
    print("\n2️⃣  UPDATE app/workflow.py - Replace run_workflow() with:")
    print("-" * 40)
    print(get_fixed_run_workflow())
    
    print("\n3️⃣  VERIFY the fix:")
    print("-" * 40)
    print("a) Check logs for: 'THREAD FIX: Using thread_id: contact-XXX'")
    print("b) Verify checkpoints.db file is created")
    print("c) Test with multiple messages from same contact")
    
    print("\n4️⃣  DEPLOY:")
    print("-" * 40)
    print("pip install -r requirements.txt")
    print("python app.py  # or your deployment command")
    
    print("\n" + "=" * 70)
    print("KEY CHANGES:")
    print("=" * 70)
    print("✅ thread_id = f'contact-{contact_id}' - ALWAYS based on contact")
    print("✅ AsyncSqliteSaver instead of MemorySaver")
    print("✅ Load existing messages from checkpoint")
    print("✅ Preserve extracted_data across messages")

if __name__ == "__main__":
    print_instructions()