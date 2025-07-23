"""
Debug Helpers - Tools for faster debugging of LangGraph applications
"""
import json
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.utils.simple_logger import get_logger

logger = get_logger("debug_helpers")


def validate_state(state: Dict[str, Any], node_name: str) -> Dict[str, Any]:
    """
    Validate state consistency and detect common issues
    
    Returns dict with validation results
    """
    results = {
        "node": node_name,
        "valid": True,
        "issues": [],
        "metrics": {}
    }
    
    messages = state.get('messages', [])
    results["metrics"]["message_count"] = len(messages)
    
    # Check for duplicates
    contents = []
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get('content', '')
        elif hasattr(msg, 'content'):
            content = msg.content
        else:
            content = str(msg)
        contents.append(content)
    
    unique_contents = set(contents)
    duplicates = len(contents) - len(unique_contents)
    results["metrics"]["duplicates"] = duplicates
    
    if duplicates > 0:
        results["valid"] = False
        results["issues"].append(f"Found {duplicates} duplicate messages")
        
        # Find which messages are duplicated
        from collections import Counter
        content_counts = Counter(contents)
        for content, count in content_counts.items():
            if count > 1:
                results["issues"].append(f"Message '{content[:50]}...' appears {count} times")
    
    # Check message types
    for i, msg in enumerate(messages):
        if isinstance(msg, dict):
            if not msg.get('type') and not msg.get('role'):
                results["issues"].append(f"Message {i} missing type/role: {msg}")
                results["valid"] = False
        elif not isinstance(msg, BaseMessage):
            results["issues"].append(f"Message {i} is not BaseMessage or dict: {type(msg)}")
            results["valid"] = False
    
    # Check for error messages
    error_count = sum(1 for c in contents if "Error" in c)
    if error_count > 0:
        results["metrics"]["error_messages"] = error_count
        results["issues"].append(f"Found {error_count} error messages")
    
    # Log validation results
    if not results["valid"]:
        logger.warning(f"State validation failed for {node_name}: {results['issues']}")
    
    return results


def log_state_transition(state: Dict[str, Any], node_name: str, phase: str = "input"):
    """
    Log detailed state information for debugging
    
    Args:
        state: Current state
        node_name: Name of the node
        phase: "input" or "output"
    """
    logger.info(f"=== {node_name.upper()} - {phase.upper()} ===")
    
    # Basic metrics
    messages = state.get('messages', [])
    logger.info(f"Messages: {len(messages)}")
    logger.info(f"Thread ID: {state.get('thread_id', 'None')}")
    logger.info(f"Contact ID: {state.get('contact_id', 'None')}")
    
    # Message details
    if messages:
        logger.info("Message breakdown:")
        human_msgs = sum(1 for m in messages if isinstance(m, HumanMessage) or (isinstance(m, dict) and m.get('role') == 'human'))
        ai_msgs = sum(1 for m in messages if isinstance(m, AIMessage) or (isinstance(m, dict) and m.get('role') == 'ai'))
        logger.info(f"  Human messages: {human_msgs}")
        logger.info(f"  AI messages: {ai_msgs}")
        logger.info(f"  Other: {len(messages) - human_msgs - ai_msgs}")
        
        # Last few messages
        logger.info("Last 3 messages:")
        for msg in messages[-3:]:
            if isinstance(msg, dict):
                content = msg.get('content', '')[:100]
                msg_type = msg.get('role', msg.get('type', 'unknown'))
            elif hasattr(msg, 'content'):
                content = str(msg.content)[:100]
                msg_type = msg.__class__.__name__
            else:
                content = str(msg)[:100]
                msg_type = type(msg).__name__
            logger.info(f"  [{msg_type}] {content}...")
    
    # Other state keys
    other_keys = [k for k in state.keys() if k not in ['messages', 'thread_id', 'contact_id']]
    if other_keys:
        logger.info(f"Other state keys: {other_keys[:5]}...")  # Show first 5
    
    logger.info(f"=== END {node_name.upper()} - {phase.upper()} ===\n")


def analyze_message_accumulation(states: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze how messages accumulate across multiple state snapshots
    
    Args:
        states: List of state snapshots from different nodes
        
    Returns:
        Analysis results
    """
    analysis = {
        "total_states": len(states),
        "accumulation_pattern": [],
        "duplication_points": [],
        "message_growth": []
    }
    
    for i, state in enumerate(states):
        node_name = state.get('__node__', f'state_{i}')
        messages = state.get('messages', [])
        msg_count = len(messages)
        
        # Track growth
        analysis["message_growth"].append({
            "node": node_name,
            "count": msg_count,
            "delta": msg_count - (analysis["message_growth"][-1]["count"] if analysis["message_growth"] else 0)
        })
        
        # Check for duplication
        validation = validate_state(state, node_name)
        if validation["metrics"].get("duplicates", 0) > 0:
            analysis["duplication_points"].append({
                "node": node_name,
                "index": i,
                "duplicates": validation["metrics"]["duplicates"],
                "issues": validation["issues"]
            })
    
    # Identify accumulation pattern
    growth_pattern = [item["delta"] for item in analysis["message_growth"]]
    if all(d > 0 for d in growth_pattern[1:]):  # Skip first
        analysis["accumulation_pattern"] = "exponential"
    elif sum(growth_pattern) > len(growth_pattern):
        analysis["accumulation_pattern"] = "linear"
    else:
        analysis["accumulation_pattern"] = "controlled"
    
    return analysis


def create_debug_wrapper(node_func):
    """
    Wrap a node function with debugging capabilities
    
    Usage:
        @create_debug_wrapper
        async def my_node(state):
            ...
    """
    import functools
    import time
    
    @functools.wraps(node_func)
    async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        node_name = node_func.__name__
        start_time = time.time()
        
        # Log input
        log_state_transition(state, node_name, "input")
        
        # Validate input
        input_validation = validate_state(state, node_name)
        
        try:
            # Call original function
            result = await node_func(state)
            
            # Log output
            log_state_transition(result, node_name, "output")
            
            # Validate output
            output_validation = validate_state(result, node_name)
            
            # Performance metrics
            duration = time.time() - start_time
            if duration > 1.0:
                logger.warning(f"{node_name} took {duration:.2f}s to execute")
            
            # Check for message explosion
            input_msgs = len(state.get('messages', []))
            output_msgs = len(result.get('messages', []))
            if output_msgs > input_msgs * 2:
                logger.error(f"{node_name} caused message explosion: {input_msgs} -> {output_msgs}")
            
            return result
            
        except Exception as e:
            logger.error(f"{node_name} failed: {str(e)}", exc_info=True)
            logger.error(f"State at failure: {json.dumps(state, default=str)[:1000]}...")
            raise
    
    return wrapper


def trace_message_flow(trace_data: Dict[str, Any]) -> None:
    """
    Analyze and print message flow from trace data
    
    Args:
        trace_data: Trace data from LangSmith or debug output
    """
    print("\n" + "="*80)
    print("MESSAGE FLOW ANALYSIS")
    print("="*80)
    
    nodes = trace_data.get('nodes', [])
    running_total = 0
    
    print(f"{'Node':<20} | {'Input':<6} | {'Output':<6} | {'Delta':<6} | {'Total':<6} | {'Status'}")
    print("-"*80)
    
    for node in nodes:
        input_count = node.get('input_messages', 0)
        output_count = node.get('output_messages', 0)
        delta = output_count - input_count
        running_total += max(0, delta)
        
        status = "✅" if delta <= 1 else "⚠️" if delta <= 2 else "❌"
        
        print(f"{node['name']:<20} | {input_count:<6} | {output_count:<6} | "
              f"{delta:+6} | {running_total:<6} | {status}")
    
    print("="*80)
    
    # Summary
    if running_total > len(nodes) * 2:
        print("⚠️ WARNING: Excessive message accumulation detected!")
    
    # Pattern detection
    deltas = [n.get('output_messages', 0) - n.get('input_messages', 0) for n in nodes]
    if all(d > 0 for d in deltas):
        print("📈 Pattern: Continuous accumulation (every node adds messages)")
    elif max(deltas) > 3:
        problem_node = nodes[deltas.index(max(deltas))]['name']
        print(f"🔍 Pattern: Spike at {problem_node} (+{max(deltas)} messages)")


def quick_trace_analysis(trace_id: str) -> Dict[str, Any]:
    """
    Quick analysis of a LangSmith trace for common issues
    
    Args:
        trace_id: LangSmith trace ID
        
    Returns:
        Analysis summary
    """
    # This would connect to LangSmith in production
    # For now, return a template for manual analysis
    return {
        "trace_id": trace_id,
        "checks": [
            "Message duplication",
            "Error messages",
            "Performance issues",
            "State consistency",
            "Node failures"
        ],
        "instructions": [
            f"1. Open https://smith.langchain.com/public/{trace_id}/r",
            "2. Check each node for message count",
            "3. Look for 'Error' in outputs",
            "4. Verify deployment version matches",
            "5. Check for exception traces"
        ]
    }