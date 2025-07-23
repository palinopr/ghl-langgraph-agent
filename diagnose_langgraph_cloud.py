#!/usr/bin/env python3
"""
Diagnose LangGraph Cloud invocation issues
"""
import json
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.workflow import workflow, ProductionState
from app.utils.debug_helpers import validate_state, analyze_message_accumulation


def diagnose_initial_state():
    """Test how the workflow handles different initial states"""
    print("="*80)
    print("TESTING INITIAL STATE HANDLING")
    print("="*80)
    
    test_cases = [
        {
            "name": "Empty messages (expected)",
            "state": {
                "messages": [],
                "contact_id": "test-123",
                "thread_id": "test-thread",
                "webhook_data": {"body": "Hola"}
            }
        },
        {
            "name": "Single message (LangGraph Cloud style?)",
            "state": {
                "messages": [HumanMessage(content="Hola")],
                "contact_id": "test-123", 
                "thread_id": "test-thread",
                "webhook_data": {"body": "Hola"}
            }
        },
        {
            "name": "Multiple messages (duplication scenario)",
            "state": {
                "messages": [
                    HumanMessage(content="Hola"),
                    HumanMessage(content="Hola"),
                    HumanMessage(content="Hola")
                ],
                "contact_id": "test-123",
                "thread_id": "test-thread", 
                "webhook_data": {"body": "Hola"}
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n[{test['name']}]")
        print(f"Initial messages: {len(test['state']['messages'])}")
        
        # Validate initial state
        validation = validate_state(test['state'], "initial")
        if not validation['valid']:
            print(f"⚠️  Initial state issues: {validation['issues']}")


def check_state_reducer():
    """Test the state reducer behavior"""
    print("\n" + "="*80)
    print("TESTING STATE REDUCER")
    print("="*80)
    
    # Simulate the lambda x, y: x + y reducer
    reducer = lambda x, y: x + y
    
    # Test scenarios
    scenarios = [
        {
            "name": "Normal append",
            "current": [HumanMessage(content="Hello")],
            "new": [AIMessage(content="Hi there!")]
        },
        {
            "name": "Empty new messages",
            "current": [HumanMessage(content="Hello")],
            "new": []
        },
        {
            "name": "Duplicate in new",
            "current": [HumanMessage(content="Hello")],
            "new": [HumanMessage(content="Hello"), AIMessage(content="Hi")]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n[{scenario['name']}]")
        print(f"Current: {len(scenario['current'])} messages")
        print(f"New: {len(scenario['new'])} messages")
        
        # Apply reducer
        result = reducer(scenario['current'], scenario['new'])
        print(f"Result: {len(result)} messages")
        
        # Check for duplicates
        contents = [m.content for m in result]
        unique = set(contents)
        if len(contents) > len(unique):
            print(f"⚠️  DUPLICATES: {len(contents) - len(unique)} duplicate messages!")


def trace_message_path():
    """Trace how messages flow through the workflow"""
    print("\n" + "="*80)
    print("MESSAGE FLOW PATH")
    print("="*80)
    
    # Show the expected flow
    flow = [
        ("1. Initial State", "messages=[] (empty)"),
        ("2. Thread Mapper", "messages=[] (pass through)"),
        ("3. Receptionist", "loads from GHL, returns new messages"),
        ("4. Intelligence", "analyzes messages"),
        ("5. Supervisor", "routes based on score"),
        ("6. Agent (Maria/Carlos/Sofia)", "processes and responds"),
        ("7. Responder", "sends to GHL")
    ]
    
    for step, desc in flow:
        print(f"{step}: {desc}")
    
    print("\n⚠️  POTENTIAL ISSUE POINTS:")
    print("- If LangGraph Cloud adds initial message → duplication at step 1")
    print("- If node returns full state → exponential growth")
    print("- If error handler doesn't use MessageManager → duplication")


def analyze_langgraph_cloud_behavior():
    """Analyze how LangGraph Cloud might be invoking the workflow"""
    print("\n" + "="*80)
    print("LANGGRAPH CLOUD INVOCATION ANALYSIS")
    print("="*80)
    
    print("\nExpected webhook invocation:")
    print(json.dumps({
        "messages": [],  # Empty
        "webhook_data": {"body": "User message"},
        "contact_id": "xxx",
        "thread_id": "xxx"
    }, indent=2))
    
    print("\nPossible LangGraph Cloud invocation:")
    print(json.dumps({
        "messages": [{"role": "human", "content": "User message"}],  # Pre-populated!
        "webhook_data": {"body": "User message"},
        "contact_id": "xxx", 
        "thread_id": "xxx"
    }, indent=2))
    
    print("\nThis would explain:")
    print("- Why first node shows 1 input message instead of 0")
    print("- Why messages duplicate (webhook_data.body + messages[0])")
    print("- Why we see 'Error' (receptionist exception handling)")


if __name__ == "__main__":
    print("LANGGRAPH CLOUD DIAGNOSTIC")
    print("=" * 80)
    
    diagnose_initial_state()
    check_state_reducer()
    trace_message_path()
    analyze_langgraph_cloud_behavior()
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    print("1. Check if LangGraph Cloud is pre-populating messages")
    print("2. Ensure thread_mapper doesn't duplicate messages") 
    print("3. Fix receptionist error handling")
    print("4. Add defensive deduplication at workflow entry")
    print("5. Log initial state in production to debug")