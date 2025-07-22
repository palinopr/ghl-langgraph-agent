#!/usr/bin/env python3
"""
Comprehensive analysis of LangSmith trace 1f0672b6-ec5a-6038-aca0-bf769eee3742
"""
import json
from datetime import datetime

# Load the trace data we already fetched
with open('trace_debug_1f0672b6_20250722_134632.json', 'r') as f:
    data = json.load(f)

trace = data['trace']

print("🔍 LANGGRAPH TRACE ANALYSIS")
print("=" * 80)

# Deployment Info
print("\n📍 DEPLOYMENT INFORMATION:")
print(f"  Deployment URL: {trace['extra']['metadata']['x-forwarded-host']}")
print(f"  LangGraph Version: {trace['extra']['metadata']['langgraph_version']}")
print(f"  Git SHA: {trace['extra']['metadata']['LANGSMITH_LANGGRAPH_GIT_REF_SHA'][:8]}")
print(f"  Thread ID (metadata): {trace['extra']['metadata']['thread_id']}")
print(f"  Thread ID (output): {trace['outputs']['thread_id']}")

# Check thread consistency
print("\n🧵 THREAD ID ANALYSIS:")
metadata_thread = trace['extra']['metadata']['thread_id']
output_thread = trace['outputs']['thread_id']
contact_id = trace['inputs']['contact_id']

print(f"  Contact ID: {contact_id}")
print(f"  Metadata Thread: {metadata_thread}")
print(f"  Output Thread: {output_thread}")
print(f"  Expected Thread: contact-{contact_id}")

if output_thread == f"contact-{contact_id}":
    print("  ✅ Thread ID follows expected pattern")
else:
    print("  ❌ Thread ID doesn't match expected pattern!")

if metadata_thread == output_thread:
    print("  ❌ ISSUE: Using metadata thread instead of contact-based thread!")

# Input/Output Analysis
print("\n📥 INPUT:")
print(f"  Message: '{trace['inputs']['messages'][0]['content']}'")
print(f"  Contact: {trace['inputs']['contact_name']} ({trace['inputs']['contact_phone']})")
print(f"  Email: {trace['inputs']['contact_email'] or 'Not provided'}")

print("\n📤 OUTPUT:")
print(f"  Response: '{trace['outputs']['messages'][-1]['content']}'")
print(f"  Lead Score: {trace['outputs']['lead_score']}")
print(f"  Lead Category: {trace['outputs']['lead_category']}")
print(f"  Agent: {trace['outputs']['messages'][-1]['name']}")

# Performance
print("\n⚡ PERFORMANCE:")
start = datetime.fromisoformat(trace['start_time'])
end = datetime.fromisoformat(trace['end_time'])
duration = (end - start).total_seconds()
print(f"  Total Duration: {duration:.2f}s")
print(f"  Token Usage: {trace['total_tokens']} (prompt: {trace['prompt_tokens']}, completion: {trace['completion_tokens']})")
print(f"  Cost: ${trace['total_cost']:.4f}")

# Child Runs Analysis
print("\n🔄 WORKFLOW NODES (Child Run IDs):")
print(f"  Total Child Runs: {len(trace['child_run_ids'])}")
print("  Direct Children:")
for i, child_id in enumerate(trace['direct_child_run_ids']):
    print(f"    {i+1}. {child_id}")

# Issues Detected
print("\n⚠️  ISSUES DETECTED:")

issues = []

# 1. Wrong response language
if "Hello!" in trace['outputs']['messages'][-1]['content']:
    issues.append("Response in English instead of Spanish (should be 'Hola')")

# 2. No agent routing
if trace['outputs']['lead_score'] == 0:
    issues.append("Lead score is 0 - no proper scoring happened")

# 3. Thread ID issue
if metadata_thread == output_thread:
    issues.append("Using LangGraph metadata thread instead of contact-based thread")

# 4. No supervisor routing visible
if 'supervisor' in trace['outputs']['messages'][-1]['name']:
    issues.append("Response came directly from supervisor - no agent routing happened")

if issues:
    for issue in issues:
        print(f"  ❌ {issue}")
else:
    print("  ✅ No major issues detected")

# Recommendations
print("\n💡 RECOMMENDATIONS:")
print("  1. Check why supervisor responded directly instead of routing to Maria")
print("  2. Verify thread_id mapping is working (should use contact-based IDs)")
print("  3. Ensure Spanish language prompts are being used")
print("  4. Check if intelligence/analyzer node ran for lead scoring")

# Summary
print("\n📊 SUMMARY:")
print(f"  This trace shows a simple 'hola' message that was handled directly by the supervisor")
print(f"  instead of being routed to an appropriate agent (should go to Maria for score 0).")
print(f"  The response was in English instead of Spanish, suggesting prompt issues.")
print(f"  Thread ID shows potential state management issues.")

print("\n🔗 View in LangSmith:")
print(f"  https://smith.langchain.com{trace['app_path']}")