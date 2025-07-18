#!/usr/bin/env python3
"""
Analyze LangSmith trace ID: 1f0640e1-3345-646e-a646-badb7f0b7adb
Focus on:
1. Whether the new responder agent is working
2. If the InvalidUpdateError is fixed
3. How many agent interactions occurred
4. Whether messages were sent to GHL
5. Any errors or issues
6. The overall flow and performance
"""
import os
import json
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize LangSmith client
client = Client(
    api_key=os.getenv("LANGSMITH_API_KEY"),
    api_url="https://api.smith.langchain.com"
)

def analyze_trace(trace_id: str):
    """Analyze a specific trace by ID"""
    print(f"\n🔍 Analyzing Trace: {trace_id}")
    print("=" * 80)
    
    try:
        # Get the run details
        run = client.read_run(trace_id)
        
        # Basic run information
        print(f"\n📊 Run Overview:")
        print(f"   Name: {run.name}")
        print(f"   Type: {run.run_type}")
        print(f"   Status: {run.status}")
        print(f"   Start: {run.start_time}")
        print(f"   End: {run.end_time}")
        if run.end_time and run.start_time:
            duration = (run.end_time - run.start_time).total_seconds()
            print(f"   Duration: {duration:.2f}s")
        
        # Error information
        if run.error:
            print(f"\n❌ ERROR DETECTED:")
            print(f"   {run.error}")
        
        # Input/Output
        print(f"\n📥 Input:")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2, ensure_ascii=False)[:500])
        
        print(f"\n📤 Output:")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2, ensure_ascii=False)[:500])
        
        # Get child runs
        child_runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=100
        ))
        
        if child_runs:
            print(f"\n🌳 Execution Tree ({len(child_runs)} child runs):")
            
            # Group by run type
            agents = []
            tools = []
            llm_calls = []
            other = []
            
            for child in child_runs:
                if child.run_type == "agent":
                    agents.append(child)
                elif child.run_type == "tool":
                    tools.append(child)
                elif child.run_type == "llm":
                    llm_calls.append(child)
                else:
                    other.append(child)
            
            # Display agents - Look for responder agent specifically
            if agents:
                print(f"\n   🤖 Agents ({len(agents)}):")
                responder_found = False
                for agent in agents:
                    status_icon = "✅" if agent.status == "success" else "❌"
                    print(f"      {status_icon} {agent.name}")
                    
                    # Check if this is the responder agent
                    if "responder" in agent.name.lower():
                        responder_found = True
                        print(f"         ⭐ RESPONDER AGENT DETECTED!")
                    
                    if agent.outputs and "messages" in agent.outputs:
                        messages = agent.outputs["messages"]
                        if messages:
                            last_msg = messages[-1]
                            if isinstance(last_msg, dict) and "content" in last_msg:
                                print(f"         → {last_msg['content'][:100]}...")
                
                if not responder_found:
                    print(f"         ⚠️  No responder agent found in this run")
            
            # Display tools
            if tools:
                print(f"\n   🔧 Tools ({len(tools)}):")
                for tool in tools:
                    status_icon = "✅" if tool.status == "success" else "❌"
                    print(f"      {status_icon} {tool.name}")
                    if tool.inputs:
                        print(f"         Input: {json.dumps(tool.inputs, ensure_ascii=False)[:100]}...")
                    if tool.outputs:
                        print(f"         Output: {json.dumps(tool.outputs, ensure_ascii=False)[:100]}...")
            
            # Display LLM calls
            if llm_calls:
                print(f"\n   💬 LLM Calls ({len(llm_calls)}):")
                for llm in llm_calls:
                    status_icon = "✅" if llm.status == "success" else "❌"
                    print(f"      {status_icon} {llm.name}")
                    if llm.outputs and "generations" in llm.outputs:
                        gens = llm.outputs["generations"]
                        if gens and len(gens) > 0 and len(gens[0]) > 0:
                            text = gens[0][0].get("text", "")
                            print(f"         → {text[:100]}...")
        
        # Look for specific patterns
        print(f"\n🔍 Specific Analysis:")
        
        # 1. Check for responder agent
        responder_runs = [r for r in child_runs if "responder" in r.name.lower()]
        if responder_runs:
            print(f"\n   ✅ Responder Agent Analysis:")
            for r in responder_runs:
                print(f"      - Status: {r.status}")
                if r.error:
                    print(f"      - Error: {r.error}")
                if r.outputs:
                    print(f"      - Output: {json.dumps(r.outputs, ensure_ascii=False)[:200]}...")
        else:
            print(f"\n   ⚠️  No responder agent runs found")
        
        # 2. Check for InvalidUpdateError
        error_found = False
        for r in [run] + child_runs:
            if r.error and "InvalidUpdateError" in str(r.error):
                error_found = True
                print(f"\n   ❌ InvalidUpdateError Found:")
                print(f"      - In: {r.name}")
                print(f"      - Error: {r.error}")
        
        if not error_found:
            print(f"\n   ✅ No InvalidUpdateError found - Issue appears to be fixed!")
        
        # 3. Check for GHL API calls
        ghl_calls = [r for r in child_runs if "ghl" in r.name.lower() or "send_message" in r.name.lower()]
        if ghl_calls:
            print(f"\n   📨 GHL API Calls ({len(ghl_calls)}):")
            for call in ghl_calls:
                print(f"      - {call.name}: {call.status}")
                if call.error:
                    print(f"        ERROR: {call.error}")
                if call.outputs:
                    print(f"        Response: {json.dumps(call.outputs, ensure_ascii=False)[:200]}...")
        else:
            print(f"\n   ⚠️  No GHL API calls found")
        
        # 4. Check for message sending
        message_tools = [r for r in child_runs if "message" in r.name.lower() and r.run_type == "tool"]
        if message_tools:
            print(f"\n   💬 Message Tools ({len(message_tools)}):")
            for tool in message_tools:
                print(f"      - {tool.name}: {tool.status}")
                if tool.inputs:
                    print(f"        Input: {json.dumps(tool.inputs, ensure_ascii=False)[:200]}...")
        
        # 5. Check final state
        if run.outputs:
            if "messages" in run.outputs:
                messages = run.outputs["messages"]
                print(f"\n   📝 Final Messages ({len(messages)}):")
                for i, msg in enumerate(messages[-3:]):  # Last 3 messages
                    if isinstance(msg, dict):
                        role = msg.get("type", "unknown")
                        content = msg.get("content", "")
                        print(f"      [{i}] {role}: {content[:150]}...")
        
        # 6. Performance metrics
        if child_runs:
            total_agents = len(agents)
            total_llm_calls = len(llm_calls)
            total_tool_calls = len(tools)
            print(f"\n   📊 Performance Metrics:")
            print(f"      - Total agents executed: {total_agents}")
            print(f"      - Total LLM calls: {total_llm_calls}")
            print(f"      - Total tool calls: {total_tool_calls}")
            print(f"      - Total duration: {duration:.2f}s")
            if total_llm_calls > 0:
                print(f"      - Avg time per LLM call: {duration/total_llm_calls:.2f}s")
        
        # Summary
        print(f"\n📋 Summary:")
        print(f"   - Run Status: {run.status}")
        print(f"   - Responder Agent: {'✅ Found' if responder_runs else '❌ Not Found'}")
        print(f"   - InvalidUpdateError: {'❌ Still Present' if error_found else '✅ Fixed'}")
        print(f"   - GHL Messages Sent: {'✅ Yes' if ghl_calls else '❌ No'}")
        print(f"   - Total Agent Interactions: {len(agents)}")
        print(f"   - Overall Performance: {duration:.2f}s")
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Analyze the specific trace
    trace_id = "1f0640e1-3345-646e-a646-badb7f0b7adb"
    analyze_trace(trace_id)