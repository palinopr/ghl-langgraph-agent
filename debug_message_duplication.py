#!/usr/bin/env python3
"""
Debug Message Duplication - Quick script to identify duplication issues
"""
import asyncio
import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from app.utils.debug_helpers import (
    validate_state,
    log_state_transition,
    analyze_message_accumulation,
    trace_message_flow,
    quick_trace_analysis
)
from app.state.message_manager import MessageManager


def simulate_duplication_issue():
    """
    Simulate the message duplication issue we encountered
    """
    print("\n" + "="*80)
    print("SIMULATING MESSAGE DUPLICATION ISSUE")
    print("="*80)
    
    # Initial state
    states = []
    
    # State 1: Initial message
    state1 = {
        "__node__": "webhook",
        "messages": [HumanMessage(content="Hola")],
        "thread_id": "test-thread",
        "contact_id": "test-contact"
    }
    states.append(state1)
    log_state_transition(state1, "webhook", "output")
    
    # State 2: After thread_mapper (incorrectly returning full state)
    state2 = {
        "__node__": "thread_mapper",
        "messages": [
            HumanMessage(content="Hola"),
            HumanMessage(content="Hola")  # Duplication!
        ],
        "thread_id": "mapped-thread",
        "contact_id": "test-contact"
    }
    states.append(state2)
    log_state_transition(state2, "thread_mapper", "output")
    
    # State 3: After receptionist (with dict vs BaseMessage issue)
    state3 = {
        "__node__": "receptionist", 
        "messages": [
            HumanMessage(content="Hola"),
            HumanMessage(content="Hola"),
            {"role": "human", "content": "Hola"},  # Same message, different format!
            {"role": "human", "content": "Hola"}
        ],
        "thread_id": "mapped-thread",
        "contact_id": "test-contact"
    }
    states.append(state3)
    log_state_transition(state3, "receptionist", "output")
    
    # Analyze accumulation
    print("\n" + "="*80)
    print("ACCUMULATION ANALYSIS")
    print("="*80)
    
    analysis = analyze_message_accumulation(states)
    print(f"Pattern: {analysis['accumulation_pattern']}")
    print(f"Growth: {[g['count'] for g in analysis['message_growth']]}")
    
    if analysis['duplication_points']:
        print("\n⚠️ DUPLICATION DETECTED at:")
        for dup in analysis['duplication_points']:
            print(f"  - {dup['node']}: {dup['duplicates']} duplicates")
            for issue in dup['issues']:
                print(f"    • {issue}")


def test_message_manager_fix():
    """
    Test the MessageManager fix for dict vs BaseMessage comparison
    """
    print("\n" + "="*80)
    print("TESTING MESSAGE MANAGER FIX")
    print("="*80)
    
    # Current messages (mix of BaseMessage and dict)
    current_messages = [
        HumanMessage(content="Hola"),
        {"role": "human", "content": "Hola"},  # Same content, different format
        AIMessage(content="Hello! How can I help you?")
    ]
    
    # New messages to add
    new_messages = [
        HumanMessage(content="Hola"),  # Duplicate
        {"role": "user", "content": "Hola"},  # Same as human, different role name
        HumanMessage(content="Como estas?"),  # New message
    ]
    
    print("Current messages:")
    for i, msg in enumerate(current_messages):
        print(f"  {i}: {type(msg).__name__ if hasattr(msg, '__class__') else 'dict'} - {msg}")
    
    print("\nNew messages to add:")
    for i, msg in enumerate(new_messages):
        print(f"  {i}: {type(msg).__name__ if hasattr(msg, '__class__') else 'dict'} - {msg}")
    
    # Test deduplication
    unique_new = MessageManager.set_messages(current_messages, new_messages)
    
    print(f"\nUnique messages to add: {len(unique_new)}")
    for msg in unique_new:
        print(f"  - {msg}")
    
    # Test full deduplication
    all_messages = current_messages + new_messages
    deduplicated = MessageManager.deduplicate_messages(all_messages)
    
    print(f"\nTotal after deduplication: {len(deduplicated)} (was {len(all_messages)})")


def debug_production_trace(trace_id: str = "1f067756-c282-640a-85ed-56c1478cd894"):
    """
    Debug a production trace
    """
    print("\n" + "="*80)
    print(f"DEBUGGING PRODUCTION TRACE: {trace_id}")
    print("="*80)
    
    # Quick analysis
    analysis = quick_trace_analysis(trace_id)
    
    print("\nQuick checks to perform:")
    for check in analysis['checks']:
        print(f"  ✓ {check}")
    
    print("\nManual steps:")
    for step in analysis['instructions']:
        print(f"  {step}")
    
    # Simulate trace data (in production, this would come from LangSmith)
    trace_data = {
        'nodes': [
            {'name': 'webhook', 'input_messages': 0, 'output_messages': 1},
            {'name': 'thread_mapper', 'input_messages': 1, 'output_messages': 2},
            {'name': 'receptionist', 'input_messages': 2, 'output_messages': 4},
            {'name': 'supervisor', 'input_messages': 4, 'output_messages': 8},
            {'name': 'responder', 'input_messages': 8, 'output_messages': 14}
        ]
    }
    
    trace_message_flow(trace_data)


def create_monitoring_dashboard():
    """
    Create a simple monitoring output for key metrics
    """
    print("\n" + "="*80)
    print("MONITORING DASHBOARD")
    print("="*80)
    
    metrics = {
        "deployment": {
            "id": "f71242bc-1ed1-4f23-9ef5-a1ce3a5b340c",
            "commit": "47b3c33",
            "status": "active"
        },
        "recent_traces": [
            {"id": "1f067756", "messages": 14, "duplicates": 10, "errors": 4},
            {"id": "1f067d49", "messages": 8, "duplicates": 6, "errors": 0},
            {"id": "1f066f7e", "messages": 4, "duplicates": 2, "errors": 0}
        ],
        "node_performance": {
            "receptionist": {"avg_time": 0.3, "error_rate": 0.25},
            "supervisor": {"avg_time": 0.5, "error_rate": 0.0},
            "responder": {"avg_time": 1.2, "error_rate": 0.0}
        }
    }
    
    print(f"Deployment: {metrics['deployment']['id'][:8]} (commit: {metrics['deployment']['commit']})")
    print(f"Status: {metrics['deployment']['status']}")
    
    print("\nRecent Traces:")
    print(f"{'Trace ID':<10} | {'Messages':<10} | {'Duplicates':<10} | {'Errors':<10}")
    print("-"*50)
    for trace in metrics['recent_traces']:
        status = "🔴" if trace['duplicates'] > 5 else "🟡" if trace['duplicates'] > 0 else "🟢"
        print(f"{trace['id']:<10} | {trace['messages']:<10} | {trace['duplicates']:<10} | {trace['errors']:<10} {status}")
    
    print("\nNode Performance:")
    for node, perf in metrics['node_performance'].items():
        status = "🔴" if perf['error_rate'] > 0.1 else "🟡" if perf['avg_time'] > 1.0 else "🟢"
        print(f"  {node}: {perf['avg_time']:.1f}s avg, {perf['error_rate']:.0%} errors {status}")


if __name__ == "__main__":
    print("MESSAGE DUPLICATION DEBUGGER")
    print("============================")
    
    # Run all debug scenarios
    simulate_duplication_issue()
    test_message_manager_fix()
    debug_production_trace()
    create_monitoring_dashboard()
    
    print("\n✅ Debug analysis complete!")
    print("\nKey findings:")
    print("1. Message duplication happens when nodes return full state")
    print("2. Dict vs BaseMessage comparison causes false duplicates")
    print("3. Error messages accumulate when not properly deduplicated")
    print("4. Use MessageManager.set_messages() in all nodes")
    print("5. Monitor trace patterns for exponential growth")