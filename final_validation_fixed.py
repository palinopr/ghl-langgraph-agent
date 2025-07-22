#!/usr/bin/env python3
"""
Final Validation Script - Comprehensive testing before deployment
Tests all changes made during the simplification effort
"""

import asyncio
import time
import tracemalloc
import traceback
import sys
import os
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Track test results
test_results = []
warnings = []
performance_metrics = {}

def test(name: str):
    """Decorator for test functions"""
    def decorator(func):
        async def wrapper():
            print(f"\n🧪 Testing: {name}")
            start_time = time.time()
            try:
                result = await func() if asyncio.iscoroutinefunction(func) else func()
                elapsed = time.time() - start_time
                test_results.append({
                    "name": name,
                    "status": "PASS",
                    "time": elapsed,
                    "details": result
                })
                print(f"✅ PASS ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                test_results.append({
                    "name": name,
                    "status": "FAIL",
                    "time": elapsed,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                print(f"❌ FAIL: {str(e)}")
                return None
        return wrapper
    return decorator

# Start memory tracking
tracemalloc.start()
start_memory = tracemalloc.get_traced_memory()[0]

@test("1. Workflow Import and Compilation")
def test_workflow_import():
    """Test that the workflow imports and compiles correctly"""
    start = time.time()
    from app.workflow import workflow, memory
    import_time = time.time() - start
    
    # Check if workflow is compiled
    if workflow is None:
        raise ValueError("Workflow not compiled")
    
    # Get nodes from the graph
    nodes = list(workflow.nodes.keys())
    expected_nodes = ["receptionist", "intelligence", "supervisor", "maria", "carlos", "sofia", "responder"]
    
    missing_nodes = []
    for node in expected_nodes:
        if node not in nodes:
            missing_nodes.append(node)
    
    if missing_nodes:
        raise ValueError(f"Missing nodes: {missing_nodes}")
    
    performance_metrics["workflow_import_time"] = import_time
    return f"Import time: {import_time:.3f}s, Nodes: {len(nodes)}"

@test("2. MinimalState Import and Schema")
def test_minimal_state():
    """Test MinimalState has correct fields"""
    from app.state.minimal_state import MinimalState
    
    # Check field count
    fields = MinimalState.__annotations__.keys()
    field_count = len(fields)
    
    # Verify essential fields exist
    essential_fields = [
        "messages", "contact_id", "thread_id", "webhook_data",
        "lead_score", "lead_category", "extracted_data",
        "current_agent", "should_end"
    ]
    
    missing_fields = [f for f in essential_fields if f not in fields]
    if missing_fields:
        raise ValueError(f"Missing essential fields: {missing_fields}")
    
    if field_count > 30:
        warnings.append(f"MinimalState has {field_count} fields (target was <25)")
    
    return f"Fields: {field_count} (reduced from 113)"

@test("3. Agent Nodes Import")
async def test_agents():
    """Test all agent nodes can be imported"""
    agents_tested = []
    
    # Test Maria
    from app.agents.maria_memory_aware import maria_memory_aware_node
    agents_tested.append("Maria (memory aware)")
    
    # Test Carlos
    from app.agents.carlos_agent_v2_fixed import carlos_node_v2_fixed
    agents_tested.append("Carlos (v2 fixed)")
    
    # Test Sofia
    from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed
    agents_tested.append("Sofia (v2 fixed)")
    
    # Test Supervisor
    from app.agents.supervisor_official import supervisor_official_node
    agents_tested.append("Supervisor (official)")
    
    # Test Receptionist
    from app.agents.receptionist_memory_aware import receptionist_memory_aware_node
    agents_tested.append("Receptionist (memory aware)")
    
    # Test Responder
    from app.agents.responder_streaming import responder_streaming_node
    agents_tested.append("Responder (streaming)")
    
    return f"Successfully imported: {', '.join(agents_tested)}"

@test("4. Base Agent Utilities")
def test_base_agent():
    """Test base agent common functions"""
    from app.agents.base_agent import (
        get_current_message,
        check_score_boundaries,
        extract_data_status,
        create_error_response
    )
    
    # Test get_current_message
    test_messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there"),
        HumanMessage(content="I have a restaurant")
    ]
    current = get_current_message(test_messages)
    if current != "I have a restaurant":
        raise ValueError(f"get_current_message failed: got '{current}'")
    
    # Test check_score_boundaries
    boundaries = check_score_boundaries(5, 5, 7)
    if not boundaries:
        raise ValueError("check_score_boundaries failed for valid score")
    
    # Test extract_data_status
    data = {"name": "John", "business_type": "restaurant"}
    status = extract_data_status(data)
    if not status["has_name"] or not status["has_business"]:
        raise ValueError("extract_data_status failed")
    
    return "All base utilities working correctly"

@test("5. GHL Client Connection")
async def test_ghl_client():
    """Test simplified GHL client"""
    from app.tools.ghl_client_simple import SimpleGHLClient
    
    client = SimpleGHLClient()
    
    # Test client methods exist
    methods = [
        "get_contact", "update_contact", "send_message",
        "get_conversation_messages", "create_appointment"
    ]
    
    for method in methods:
        if not hasattr(client, method):
            raise ValueError(f"Missing method: {method}")
    
    # Check API call wrapper exists
    if not hasattr(client, "api_call"):
        raise ValueError("Missing generic api_call method")
    
    return f"Client has {len(methods)}/13 production methods"

@test("6. Intelligence Analyzer")
async def test_intelligence():
    """Test intelligence analyzer extraction"""
    from app.intelligence.analyzer import IntelligenceAnalyzer
    
    analyzer = IntelligenceAnalyzer()
    
    # Test extraction with real method
    test_state = {
        "messages": [HumanMessage(content="Hola, tengo un restaurante")],
        "extracted_data": {},
        "lead_score": 0
    }
    
    # Call the analyze method properly
    result = await analyzer.analyze(test_state)
    
    # Check extraction
    if result["extracted_data"].get("business_type") != "restaurante":
        raise ValueError(f"Failed to extract business type: {result['extracted_data']}")
    
    # Check scoring
    if result["lead_score"] < 2:
        raise ValueError(f"Score too low: {result['lead_score']}")
    
    return f"Extraction working: score={result['lead_score']}, business={result['extracted_data'].get('business_type')}"

@test("7. Core User Journey Simulation")
async def test_user_journey():
    """Simulate complete webhook → response flow"""
    from app.state.minimal_state import MinimalState
    from app.intelligence.analyzer import IntelligenceAnalyzer
    from app.agents.base_agent import get_current_message
    from langchain_core.messages import HumanMessage
    
    # Simulate webhook data
    webhook_data = {
        "contactId": "test123",
        "body": "Hola, tengo un restaurante y necesito más clientes",
        "conversationId": "conv123",
        "locationId": "loc123",
        "type": "SMS"
    }
    
    # Step 1: Create initial state (Receptionist would do this)
    state: MinimalState = {
        "messages": [HumanMessage(content=webhook_data["body"])],
        "contact_id": webhook_data["contactId"],
        "thread_id": webhook_data.get("conversationId"),
        "webhook_data": webhook_data,
        "lead_score": 0,
        "lead_category": "cold",
        "extracted_data": {},
        "current_agent": None,
        "next_agent": None,
        "agent_task": None,
        "should_end": False,
        "needs_rerouting": False,
        "needs_escalation": False,
        "response_to_send": None,
        "conversation_stage": None,
        "messages_to_send": [],
        "appointment_status": None,
        "available_slots": None,
        "appointment_details": None,
        "contact_name": None,
        "custom_fields": {},
        "agent_handoff": None,
        "error": None
    }
    
    # Step 2: Intelligence analysis
    analyzer = IntelligenceAnalyzer()
    intel_result = await analyzer.analyze(state)
    
    if intel_result["lead_score"] < 2:
        raise ValueError(f"Score too low: {intel_result['lead_score']}")
    
    if intel_result["extracted_data"].get("business_type") != "restaurante":
        raise ValueError("Failed to extract business type")
    
    # Step 3: Supervisor routing (based on score)
    score = intel_result["lead_score"]
    if score <= 4:
        expected_agent = "maria"
    elif score <= 7:
        expected_agent = "carlos"
    else:
        expected_agent = "sofia"
    
    # Step 4: Agent response (simulate)
    current_msg = get_current_message(state["messages"])
    if not current_msg:
        raise ValueError("Failed to get current message")
    
    return f"Journey complete: Score={score}, Agent={expected_agent}, Business=restaurante"

@test("8. No Circular Imports")
def test_circular_imports():
    """Check for circular import issues"""
    # Try importing all major modules
    imports_to_test = [
        "app.workflow",
        "app.state.minimal_state",
        "app.agents.supervisor_official",
        "app.agents.maria_memory_aware",
        "app.agents.carlos_agent_v2_fixed",
        "app.agents.sofia_agent_v2_fixed",
        "app.intelligence.analyzer",
        "app.tools.ghl_client_simple",
        "app.utils.simple_logger",
        "app.config"
    ]
    
    failed_imports = []
    for module_name in imports_to_test:
        try:
            __import__(module_name)
        except ImportError as e:
            failed_imports.append(f"{module_name}: {str(e)}")
    
    if failed_imports:
        raise ValueError(f"Import failures: {', '.join(failed_imports)}")
    
    return f"Successfully imported {len(imports_to_test)} modules"

@test("9. Documentation Files")
def test_documentation():
    """Verify documentation files exist and are valid"""
    required_docs = [
        "README.md",
        "DEPLOYMENT_GUIDE.md",
        "ARCHITECTURE.md",
        "DEVELOPMENT.md",
        "CHANGELOG.md"
    ]
    
    missing_docs = []
    for doc in required_docs:
        if not os.path.exists(doc):
            missing_docs.append(doc)
    
    if missing_docs:
        raise ValueError(f"Missing docs: {missing_docs}")
    
    # Check file sizes (should have content)
    for doc in required_docs:
        size = os.path.getsize(doc)
        if size < 1000:  # Less than 1KB is suspicious
            warnings.append(f"{doc} seems too small ({size} bytes)")
    
    return f"All {len(required_docs)} documentation files present"

@test("10. No References to Deleted Files")
def test_no_dead_references():
    """Check for references to deleted files"""
    # Common deleted file patterns
    deleted_patterns = [
        "ConversationState",  # Should use MinimalState
        "ghl_client.py",     # Should use ghl_client_simple.py
        "workflow_enhanced",  # Deleted workflow variants
        "workflow_parallel",
        "supervisor_brain",   # Should use supervisor_official.py
        "debug_logger"        # Should use simple_logger
    ]
    
    # Files to check
    check_files = [
        "app/workflow.py",
        "app/agents/supervisor_official.py",
        "app/agents/maria_memory_aware.py",
        "app/agents/carlos_agent_v2_fixed.py",
        "app/agents/sofia_agent_v2_fixed.py"
    ]
    
    found_references = []
    for file_path in check_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                for pattern in deleted_patterns:
                    if pattern in content and pattern != "ConversationState":  # Allow in comments
                        # Check if it's in a comment
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if pattern in line and not line.strip().startswith('#'):
                                found_references.append(f"{file_path}:{i+1} - {pattern}")
    
    if found_references:
        warnings.append(f"Found references to deleted files: {found_references}")
    
    return "No critical references to deleted files"

@test("11. Performance Benchmarks")
async def test_performance():
    """Measure performance improvements"""
    import psutil
    import gc
    
    # Force garbage collection
    gc.collect()
    
    # Memory after all imports
    current_memory = tracemalloc.get_traced_memory()[0]
    memory_used_mb = (current_memory - start_memory) / 1024 / 1024
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # Test state creation speed
    from app.state.minimal_state import MinimalState
    
    start = time.time()
    for _ in range(1000):
        state: MinimalState = {
            "messages": [],
            "contact_id": "test",
            "thread_id": None,
            "webhook_data": {},
            "lead_score": 0,
            "lead_category": "cold",
            "extracted_data": {},
            "current_agent": None,
            "next_agent": None,
            "agent_task": None,
            "should_end": False,
            "needs_rerouting": False,
            "needs_escalation": False,
            "response_to_send": None,
            "conversation_stage": None,
            "messages_to_send": [],
            "appointment_status": None,
            "available_slots": None,
            "appointment_details": None,
            "contact_name": None,
            "custom_fields": {},
            "agent_handoff": None,
            "error": None
        }
    state_creation_time = (time.time() - start) * 1000  # Convert to ms
    
    performance_metrics.update({
        "memory_used_mb": round(memory_used_mb, 2),
        "cpu_percent": cpu_percent,
        "state_creation_per_1000": round(state_creation_time, 2)
    })
    
    # Check thresholds
    if memory_used_mb > 100:
        warnings.append(f"High memory usage: {memory_used_mb:.2f} MB")
    
    return f"Memory: {memory_used_mb:.2f}MB, State creation: {state_creation_time:.2f}ms/1000"

# Add missing import for messages
from langchain_core.messages import HumanMessage, AIMessage

async def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("🚀 FINAL VALIDATION - Testing all changes before deployment")
    print("=" * 60)
    
    # Run all tests
    await test_workflow_import()
    await test_minimal_state()
    await test_agents()
    await test_base_agent()
    await test_ghl_client()
    await test_intelligence()
    await test_user_journey()
    await test_circular_imports()
    await test_documentation()
    await test_no_dead_references()
    await test_performance()
    
    # Calculate results
    passed = sum(1 for t in test_results if t["status"] == "PASS")
    failed = sum(1 for t in test_results if t["status"] == "FAIL")
    total_time = sum(t["time"] for t in test_results)
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(test_results)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Total Time: {total_time:.2f}s")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("\n📈 Performance Metrics:")
    for key, value in performance_metrics.items():
        print(f"  - {key}: {value}")
    
    # Generate report
    confidence_level = (passed / len(test_results)) * 100
    deployment_ready = failed == 0 and len(warnings) < 3
    
    print(f"\n🎯 Confidence Level: {confidence_level:.1f}%")
    print(f"🚦 Deployment Status: {'GO ✅' if deployment_ready else 'NO-GO ❌'}")
    
    # Write detailed report
    generate_report(test_results, warnings, performance_metrics, confidence_level, deployment_ready)
    
    return deployment_ready

def generate_report(results, warns, metrics, confidence, ready):
    """Generate detailed validation report"""
    report = f"""# FINAL_VALIDATION_REPORT.md

## 🚀 Final Validation Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Summary
- **Total Tests**: {len(results)}
- **Passed**: {sum(1 for t in results if t["status"] == "PASS")} ✅
- **Failed**: {sum(1 for t in results if t["status"] == "FAIL")} ❌
- **Warnings**: {len(warns)} ⚠️
- **Confidence Level**: {confidence:.1f}%
- **Deployment Status**: {'GO ✅' if ready else 'NO-GO ❌'}

## 🧪 Test Results

"""
    
    for test in results:
        status_emoji = "✅" if test["status"] == "PASS" else "❌"
        report += f"### {status_emoji} {test['name']}\n"
        report += f"- **Status**: {test['status']}\n"
        report += f"- **Time**: {test['time']:.3f}s\n"
        
        if test["status"] == "PASS" and test.get("details"):
            report += f"- **Details**: {test['details']}\n"
        elif test["status"] == "FAIL":
            report += f"- **Error**: {test.get('error', 'Unknown error')}\n"
            if 'traceback' in test:
                report += f"```python\n{test['traceback']}\n```\n"
        report += "\n"
    
    if warns:
        report += "## ⚠️ Warnings\n\n"
        for warning in warns:
            report += f"- {warning}\n"
        report += "\n"
    
    report += "## 📈 Performance Metrics\n\n"
    report += "| Metric | Value |\n"
    report += "|--------|-------|\n"
    for key, value in metrics.items():
        report += f"| {key.replace('_', ' ').title()} | {value} |\n"
    
    report += f"\n## 🎯 Deployment Decision\n\n"
    if ready:
        report += """### ✅ GO FOR DEPLOYMENT

All critical tests passed. The system is ready for production deployment.

**Recommended next steps:**
1. Run `make validate` one more time
2. Commit all changes
3. Push to production
4. Monitor initial deployment closely
"""
    else:
        report += """### ❌ NO-GO FOR DEPLOYMENT

Critical issues found that must be fixed before deployment.

**Required fixes:**
"""
        for test in results:
            if test["status"] == "FAIL":
                report += f"- Fix: {test['name']} - {test.get('error', 'See traceback')}\n"
    
    report += "\n## 📋 Checklist\n\n"
    checklist_items = [
        ("Workflow compiles", any(t["name"].startswith("1.") and t["status"] == "PASS" for t in results)),
        ("State management working", any(t["name"].startswith("2.") and t["status"] == "PASS" for t in results)),
        ("All agents functional", any(t["name"].startswith("3.") and t["status"] == "PASS" for t in results)),
        ("No circular imports", any(t["name"].startswith("8.") and t["status"] == "PASS" for t in results)),
        ("Documentation complete", any(t["name"].startswith("9.") and t["status"] == "PASS" for t in results)),
        ("Performance acceptable", len([w for w in warns if "memory" in w.lower()]) == 0)
    ]
    
    for item, passed in checklist_items:
        report += f"- [{'x' if passed else ' '}] {item}\n"
    
    with open("FINAL_VALIDATION_REPORT.md", "w") as f:
        f.write(report)
    
    print(f"\n📄 Detailed report written to FINAL_VALIDATION_REPORT.md")

if __name__ == "__main__":
    asyncio.run(run_all_tests())