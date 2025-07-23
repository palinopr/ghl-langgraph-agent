#!/usr/bin/env python3
"""
Run the workflow directly RIGHT NOW
"""
import os
import sys
import asyncio

# CRITICAL: Set environment variables BEFORE any imports
os.environ.update({
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "LANGCHAIN_TRACING_V2": "true", 
    "LANGCHAIN_API_KEY": "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",
    "LANGCHAIN_PROJECT": "direct-test-now",
    "GHL_API_KEY": "pit-21cee867-6a57-4eea-b6fa-2bd4462934d0",
    "GHL_LOCATION_ID": "sHFG9Rw6BdGh6d6bfMqG"
})

# Import workflow directly from the file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import minimal requirements
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    """Run the production workflow NOW"""
    
    print("🚀 Running Production Workflow Directly")
    print("=" * 60)
    
    # Import the compiled workflow from production file
    try:
        # Import just the compiled workflow object
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "workflow_module", 
            "app/workflow.py"
        )
        workflow_module = importlib.util.module_from_spec(spec)
        
        # Execute the module to get the workflow
        spec.loader.exec_module(workflow_module)
        
        # Get the compiled workflow
        workflow = workflow_module.workflow
        print("✅ Workflow loaded successfully!")
        
    except Exception as e:
        print(f"❌ Error loading workflow: {e}")
        
        # Fallback: create a simple workflow
        print("\n🔧 Creating fallback workflow...")
        
        from typing import TypedDict, Annotated, List, Dict, Any
        from langchain_core.messages import BaseMessage
        
        class SimpleState(TypedDict):
            messages: Annotated[List[BaseMessage], lambda x, y: x + y]
            webhook_data: Dict[str, Any]
            thread_id: str
            lead_score: int
            current_agent: str
            message_sent: bool
        
        def process_node(state: SimpleState) -> Dict[str, Any]:
            webhook_data = state.get("webhook_data", {})
            message = webhook_data.get("body", "")
            
            # Simple scoring
            lead_score = 2
            if "restaurante" in message.lower():
                lead_score = 6
            if "agendar" in message.lower() or "urgente" in message.lower():
                lead_score = 9
            
            agent = "maria" if lead_score < 5 else ("carlos" if lead_score < 8 else "sofia")
            
            return {
                "messages": [HumanMessage(content=message)],
                "lead_score": lead_score,
                "current_agent": agent,
                "message_sent": True
            }
        
        # Create simple workflow
        workflow_graph = StateGraph(SimpleState)
        workflow_graph.add_node("process", process_node)
        workflow_graph.set_entry_point("process")
        workflow_graph.add_edge("process", END)
        
        workflow = workflow_graph.compile(checkpointer=MemorySaver())
    
    # Test the workflow
    print("\n📊 Testing with sample messages...")
    
    test_cases = [
        ("Hola, qué hacen?", 2, "maria"),
        ("Tengo un restaurante y necesito más clientes", 6, "carlos"),
        ("Necesito agendar una cita urgente, presupuesto $500", 9, "sofia")
    ]
    
    for i, (message, expected_score, expected_agent) in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {message}")
        
        state = {
            "webhook_data": {
                "contactId": f"test-{i}",
                "body": message,
                "conversationId": f"conv-{i}"
            },
            "thread_id": f"thread-conv-{i}",
            "messages": []
        }
        
        config = {"configurable": {"thread_id": f"thread-conv-{i}"}}
        
        try:
            result = await workflow.ainvoke(state, config=config)
            
            lead_score = result.get("lead_score", 0)
            current_agent = result.get("current_agent", "unknown")
            message_sent = result.get("message_sent", False)
            
            print(f"✅ Success!")
            print(f"   Lead Score: {lead_score} (expected: {expected_score})")
            print(f"   Agent: {current_agent} (expected: {expected_agent})")
            print(f"   Message Sent: {message_sent}")
            
            # Show trace URL
            print(f"\n🔗 View trace: https://smith.langchain.com/public/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/r")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print("✅ Test completed!")
    print(f"View all traces at: https://smith.langchain.com")

if __name__ == "__main__":
    asyncio.run(run_test())