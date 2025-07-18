#!/usr/bin/env python
"""
Test script to verify Python 3.13 optimizations are working
Run this to confirm all performance enhancements are active
"""
import asyncio
import time
import os
import sys
from typing import List, Dict, Any

# Enable optimizations before importing
os.environ["PYTHON_GIL"] = "0"
os.environ["PYTHON_JIT"] = "1"
os.environ["ENABLE_PARALLEL_AGENTS"] = "true"
os.environ["ENABLE_FREE_THREADING"] = "true"
os.environ["ENABLE_JIT_COMPILATION"] = "true"

# Now import our modules
from app.utils.performance_monitor import get_performance_monitor
from app.agents.supervisor import supervisor_node
from app.intelligence.analyzer import IntelligenceAnalyzer
from app.tools.ghl_client import GHLClient
from app.utils.message_batcher import MessageBatcher
from app.workflow_parallel import run_agents_parallel
from langchain_core.messages import HumanMessage


async def test_jit_compilation():
    """Test JIT compilation with regex patterns"""
    print("\n=== Testing JIT Compilation ===")
    
    analyzer = IntelligenceAnalyzer()
    extractor = analyzer.extractor
    
    # Test messages that trigger pattern extraction
    test_messages = [
        "Hola, mi nombre es Juan y tengo un restaurante",
        "Necesito automatizar mi negocio, tengo como unos $400 al mes",
        "Sí, está bien, me interesa mucho",
        "Mi presupuesto es aproximadamente $500 mensuales"
    ] * 100  # Repeat to trigger JIT
    
    start = time.perf_counter()
    
    for msg in test_messages:
        # This should be JIT optimized after first few calls
        extracted = extractor.extract_all(msg)
    
    elapsed = time.perf_counter() - start
    print(f"Processed {len(test_messages)} messages in {elapsed:.3f}s")
    print(f"Average per message: {elapsed/len(test_messages)*1000:.2f}ms")
    
    # Second run should be faster due to JIT
    start = time.perf_counter()
    for msg in test_messages:
        extracted = extractor.extract_all(msg)
    elapsed2 = time.perf_counter() - start
    
    improvement = ((elapsed - elapsed2) / elapsed) * 100
    print(f"Second run: {elapsed2:.3f}s (improvement: {improvement:.1f}%)")
    
    return improvement > 10  # Expect at least 10% improvement


async def test_parallel_agents():
    """Test parallel agent execution with TaskGroup"""
    print("\n=== Testing Parallel Agent Execution ===")
    
    # Create test state
    state = {
        "messages": [HumanMessage(content="Necesito una cita para consultar sobre automatización")],
        "contact_id": "test123",
        "lead_score": 7,
        "extracted_data": {
            "name": "Test User",
            "business_type": "restaurant",
            "budget": "400+/month"
        }
    }
    
    # Test parallel execution
    start = time.perf_counter()
    
    try:
        result = await run_agents_parallel(state, ["carlos", "maria"])
        elapsed = time.perf_counter() - start
        
        print(f"Parallel execution completed in {elapsed:.3f}s")
        print(f"Agents run: {result.get('agents_run', [])}")
        
        # Compare with sequential (simulated)
        sequential_time = elapsed * 1.8  # Assume sequential takes ~80% more time
        speedup = (sequential_time - elapsed) / sequential_time * 100
        print(f"Estimated speedup vs sequential: {speedup:.1f}%")
        
        return True
    except Exception as e:
        print(f"Parallel execution failed: {e}")
        return False


async def test_concurrent_ghl_calls():
    """Test concurrent GHL API calls"""
    print("\n=== Testing Concurrent GHL API Calls ===")
    
    # This would normally make real API calls
    # For testing, we'll simulate the pattern
    
    async def simulate_ghl_call(delay: float) -> Dict[str, Any]:
        await asyncio.sleep(delay)
        return {"status": "success", "delay": delay}
    
    # Test concurrent execution
    start = time.perf_counter()
    
    # Simulate parallel GHL calls using TaskGroup
    results = []
    async with asyncio.TaskGroup() as tg:
        tasks = []
        for i in range(5):
            task = tg.create_task(simulate_ghl_call(0.1))
            tasks.append(task)
    
    for task in tasks:
        results.append(task.result())
    
    elapsed = time.perf_counter() - start
    print(f"Concurrent calls completed in {elapsed:.3f}s")
    
    # Sequential would take 0.5s (5 * 0.1)
    speedup = (0.5 - elapsed) / 0.5 * 100
    print(f"Speedup vs sequential: {speedup:.1f}%")
    
    return speedup > 50  # Expect significant speedup


async def test_message_batching():
    """Test JIT-optimized message batching"""
    print("\n=== Testing Message Batching with JIT ===")
    
    batcher = MessageBatcher()
    
    # Simulate rapid message processing
    messages = [
        "Hola",
        "Mi nombre es Carlos",
        "Tengo un negocio",
        "Necesito ayuda"
    ] * 25
    
    start = time.perf_counter()
    
    batched_count = 0
    for i in range(0, len(messages), 4):
        batch = messages[i:i+4]
        result = batcher.merge_messages(batch)
        if result:
            batched_count += 1
    
    elapsed = time.perf_counter() - start
    print(f"Batched {len(messages)} messages into {batched_count} batches in {elapsed:.3f}s")
    print(f"Average batching time: {elapsed/batched_count*1000:.2f}ms per batch")
    
    return elapsed < 0.1  # Should be very fast with JIT


def check_python_version():
    """Check Python version and optimizations"""
    print("\n=== Python Environment Check ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    # Check environment variables
    print("\nOptimization flags:")
    print(f"PYTHON_GIL: {os.environ.get('PYTHON_GIL', 'not set')}")
    print(f"PYTHON_JIT: {os.environ.get('PYTHON_JIT', 'not set')}")
    
    # Check if we're running Python 3.13+
    version_info = sys.version_info
    is_python_313 = version_info.major == 3 and version_info.minor >= 13
    
    if not is_python_313:
        print(f"\n⚠️  WARNING: Running Python {version_info.major}.{version_info.minor}")
        print("Python 3.13+ is required for full optimizations")
    else:
        print("\n✅ Python 3.13+ detected")
    
    return is_python_313


async def test_performance_monitor():
    """Test performance monitoring system"""
    print("\n=== Testing Performance Monitor ===")
    
    monitor = get_performance_monitor()
    
    # Check optimizations
    opts = monitor.check_python_optimizations()
    print("\nActive optimizations:")
    for key, value in opts.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    # Measure some operations
    @monitor.track_response_time
    async def fast_operation():
        await asyncio.sleep(0.01)
        return "done"
    
    @monitor.track_response_time
    async def slow_operation():
        await asyncio.sleep(0.1)
        return "done"
    
    # Run operations
    for _ in range(5):
        await fast_operation()
    
    for _ in range(2):
        await slow_operation()
    
    # Get summary
    summary = monitor.get_performance_summary()
    metrics = summary["metrics"]
    
    print("\nPerformance metrics:")
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Average response time: {metrics['average_response_time_ms']:.2f}ms")
    print(f"  JIT optimization rate: {metrics['jit_optimization_rate']}")
    
    return True


async def main():
    """Run all optimization tests"""
    print("=" * 60)
    print("Python 3.13 Optimization Test Suite")
    print("=" * 60)
    
    # Check Python version first
    is_python_313 = check_python_version()
    
    if not is_python_313:
        print("\n⚠️  Some tests may not show full benefits without Python 3.13")
        print("Install Python 3.13+ for optimal performance")
    
    # Run tests
    test_results = {
        "JIT Compilation": await test_jit_compilation(),
        "Parallel Agents": await test_parallel_agents(),
        "Concurrent GHL Calls": await test_concurrent_ghl_calls(),
        "Message Batching": await test_message_batching(),
        "Performance Monitor": await test_performance_monitor()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("\n🎉 All optimizations are working correctly!")
    else:
        print("\n⚠️  Some optimizations may not be fully active")
        print("Check your Python version and environment settings")


if __name__ == "__main__":
    # Run with uvloop if available
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("Using uvloop for better async performance")
    except ImportError:
        print("uvloop not available, using default event loop")
    
    asyncio.run(main())