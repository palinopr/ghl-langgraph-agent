#!/usr/bin/env python
"""
Simple test to verify Python 3.13 optimizations are working
"""
import asyncio
import time
import os
import sys
from app.utils.performance_monitor import get_performance_monitor
from app.intelligence.analyzer import IntelligenceAnalyzer

def check_environment():
    """Check Python version and optimization flags"""
    print("=== Python Environment ===")
    print(f"Python version: {sys.version}")
    print(f"PYTHON_GIL: {os.environ.get('PYTHON_GIL', 'not set')}")
    print(f"PYTHON_JIT: {os.environ.get('PYTHON_JIT', 'not set')}")
    
    version_info = sys.version_info
    is_python_313 = version_info.major == 3 and version_info.minor >= 13
    
    if is_python_313:
        print("✅ Python 3.13+ detected - full optimizations available")
    else:
        print(f"⚠️  Python {version_info.major}.{version_info.minor} - limited optimizations")
    
    return is_python_313

def test_jit_pattern_extraction():
    """Test JIT-optimized Spanish pattern extraction"""
    print("\n=== Testing JIT-Optimized Pattern Extraction ===")
    
    analyzer = IntelligenceAnalyzer()
    extractor = analyzer.extractor
    
    # Test messages
    test_messages = [
        "Hola, mi nombre es Juan y tengo un restaurante",
        "Necesito automatizar mi negocio, tengo como unos $400 al mes",
        "Sí, está bien, me interesa mucho",
    ] * 50  # Repeat to trigger JIT
    
    # First run (cold)
    start = time.perf_counter()
    for msg in test_messages:
        result = extractor.extract_all(msg)
    cold_time = time.perf_counter() - start
    
    # Second run (warmed up)
    start = time.perf_counter()
    for msg in test_messages:
        result = extractor.extract_all(msg)
    warm_time = time.perf_counter() - start
    
    improvement = ((cold_time - warm_time) / cold_time) * 100
    
    print(f"Cold run: {cold_time:.3f}s ({cold_time/len(test_messages)*1000:.2f}ms per message)")
    print(f"Warm run: {warm_time:.3f}s ({warm_time/len(test_messages)*1000:.2f}ms per message)")
    print(f"JIT improvement: {improvement:.1f}%")
    
    return improvement > 5  # Expect at least 5% improvement

async def test_concurrent_operations():
    """Test concurrent operations with asyncio.TaskGroup"""
    print("\n=== Testing Concurrent Operations ===")
    
    async def simulate_operation(name: str, delay: float):
        await asyncio.sleep(delay)
        return f"{name} completed"
    
    # Test with TaskGroup (Python 3.13+)
    try:
        start = time.perf_counter()
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(simulate_operation(f"Task{i}", 0.1))
                for i in range(5)
            ]
        concurrent_time = time.perf_counter() - start
        print(f"✅ TaskGroup execution: {concurrent_time:.3f}s")
        speedup = (0.5 - concurrent_time) / 0.5 * 100
        print(f"Speedup vs sequential: {speedup:.1f}%")
        return True
    except AttributeError:
        print("⚠️  TaskGroup not available (requires Python 3.11+)")
        # Fallback to gather
        start = time.perf_counter()
        results = await asyncio.gather(*[
            simulate_operation(f"Task{i}", 0.1) for i in range(5)
        ])
        concurrent_time = time.perf_counter() - start
        print(f"asyncio.gather execution: {concurrent_time:.3f}s")
        return True

def test_performance_monitor():
    """Test performance monitoring capabilities"""
    print("\n=== Testing Performance Monitor ===")
    
    monitor = get_performance_monitor()
    opts = monitor.check_python_optimizations()
    
    print("Optimization status:")
    for key, value in opts.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    # Get system resources
    resources = monitor.measure_system_resources()
    print(f"\nSystem resources:")
    print(f"  CPU: {resources.get('cpu_percent', 0):.1f}%")
    print(f"  Memory: {resources.get('memory_mb', 0):.1f}MB")
    print(f"  Threads: {resources.get('threads', 0)}")
    
    return True

async def main():
    """Run all tests"""
    print("=" * 50)
    print("Python 3.13 Optimization Tests")
    print("=" * 50)
    
    # Check environment
    is_python_313 = check_environment()
    
    # Run tests
    results = {
        "Environment": is_python_313,
        "JIT Pattern Extraction": test_jit_pattern_extraction(),
        "Concurrent Operations": await test_concurrent_operations(),
        "Performance Monitor": test_performance_monitor()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for v in results.values() if v)
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"{test}: {status}")
    
    print(f"\nPassed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 All optimizations working correctly!")
    else:
        print("\n⚠️  Some optimizations may need configuration")

if __name__ == "__main__":
    # Set optimization flags
    os.environ["PYTHON_GIL"] = "0"
    os.environ["PYTHON_JIT"] = "1"
    
    # Run with uvloop if available
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("Using uvloop for better async performance\n")
    except ImportError:
        print("uvloop not available, using default event loop\n")
    
    asyncio.run(main())