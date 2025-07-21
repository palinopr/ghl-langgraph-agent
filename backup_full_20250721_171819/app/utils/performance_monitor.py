"""
Performance monitoring for Python 3.13 optimizations
Tracks JIT compilation, free-threading benefits, and parallel execution metrics
"""
import time
import asyncio
import psutil
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("performance_monitor")


class PerformanceMonitor:
    """Monitor Python 3.13 performance optimizations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.metrics = {
            "jit_compilations": 0,
            "parallel_executions": 0,
            "gil_contentions": 0,
            "async_tasks": 0,
            "response_times": [],
            "memory_usage": [],
            "cpu_usage": []
        }
        self._start_time = time.time()
        self._process = psutil.Process()
        
    def check_python_optimizations(self) -> Dict[str, Any]:
        """Check which Python 3.13 optimizations are active"""
        import os
        
        optimizations = {
            "python_version": sys.version,
            "gil_disabled": os.environ.get("PYTHON_GIL") == "0",
            "jit_enabled": os.environ.get("PYTHON_JIT") == "1",
            "free_threading": self.settings.enable_free_threading,
            "parallel_agents": self.settings.enable_parallel_agents,
            "concurrent_webhooks": self.settings.enable_concurrent_webhooks
        }
        
        # Check if asyncio is using uvloop
        try:
            import uvloop
            optimizations["uvloop_available"] = True
        except ImportError:
            optimizations["uvloop_available"] = False
            
        return optimizations
    
    def track_response_time(self, func):
        """Decorator to track function response times"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self.metrics["response_times"].append(elapsed)
                
                if elapsed < 0.1:  # Sub-100ms indicates JIT optimization
                    self.metrics["jit_compilations"] += 1
                    
                return result
            finally:
                self._log_performance(func.__name__, time.perf_counter() - start)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self.metrics["response_times"].append(elapsed)
                return result
            finally:
                self._log_performance(func.__name__, time.perf_counter() - start)
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def track_parallel_execution(self, agent_names: List[str]):
        """Track parallel agent execution"""
        self.metrics["parallel_executions"] += 1
        logger.info(f"Parallel execution tracked for agents: {agent_names}")
        
    def track_async_task(self):
        """Track async task creation"""
        self.metrics["async_tasks"] += 1
        
    def measure_system_resources(self):
        """Measure current system resource usage"""
        try:
            # CPU usage
            cpu_percent = self._process.cpu_percent(interval=0.1)
            self.metrics["cpu_usage"].append(cpu_percent)
            
            # Memory usage
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.metrics["memory_usage"].append(memory_mb)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "threads": self._process.num_threads()
            }
        except Exception as e:
            logger.error(f"Failed to measure system resources: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        uptime = time.time() - self._start_time
        
        # Calculate averages
        avg_response_time = (
            sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            if self.metrics["response_times"] else 0
        )
        
        avg_cpu = (
            sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"])
            if self.metrics["cpu_usage"] else 0
        )
        
        avg_memory = (
            sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"])
            if self.metrics["memory_usage"] else 0
        )
        
        # JIT optimization rate
        jit_rate = (
            self.metrics["jit_compilations"] / len(self.metrics["response_times"])
            if self.metrics["response_times"] else 0
        )
        
        summary = {
            "uptime_seconds": uptime,
            "optimizations": self.check_python_optimizations(),
            "metrics": {
                "total_requests": len(self.metrics["response_times"]),
                "average_response_time_ms": avg_response_time * 1000,
                "jit_optimization_rate": f"{jit_rate * 100:.1f}%",
                "parallel_executions": self.metrics["parallel_executions"],
                "async_tasks_created": self.metrics["async_tasks"],
                "average_cpu_percent": f"{avg_cpu:.1f}%",
                "average_memory_mb": f"{avg_memory:.1f}",
                "current_resources": self.measure_system_resources()
            },
            "performance_gains": self._calculate_performance_gains()
        }
        
        return summary
    
    def _calculate_performance_gains(self) -> Dict[str, str]:
        """Calculate performance gains from optimizations"""
        gains = {}
        
        # Response time improvements
        if self.metrics["response_times"]:
            recent_times = self.metrics["response_times"][-100:]
            early_times = self.metrics["response_times"][:100]
            
            if len(early_times) >= 10 and len(recent_times) >= 10:
                early_avg = sum(early_times) / len(early_times)
                recent_avg = sum(recent_times) / len(recent_times)
                improvement = ((early_avg - recent_avg) / early_avg) * 100
                gains["response_time_improvement"] = f"{improvement:.1f}%"
        
        # Parallel execution benefits
        if self.metrics["parallel_executions"] > 0:
            gains["parallel_execution_ratio"] = (
                f"{self.metrics['parallel_executions'] / len(self.metrics['response_times']) * 100:.1f}%"
            )
        
        # JIT compilation benefits
        if self.metrics["jit_compilations"] > 0:
            gains["jit_optimized_calls"] = f"{self.metrics['jit_compilations']}"
        
        return gains
    
    def _log_performance(self, operation: str, duration: float):
        """Log performance metrics"""
        if duration > 1.0:  # Log slow operations
            logger.warning(f"Slow operation: {operation} took {duration:.2f}s")
        elif self.settings.enable_performance_monitoring and duration < 0.05:
            logger.debug(f"Fast operation (likely JIT): {operation} took {duration*1000:.1f}ms")
    
    async def periodic_monitoring(self):
        """Run periodic performance monitoring"""
        while True:
            try:
                await asyncio.sleep(self.settings.performance_log_interval)
                
                summary = self.get_performance_summary()
                logger.info(f"Performance summary: {summary}")
                
                # Alert on high resource usage
                current = summary["metrics"]["current_resources"]
                if current.get("cpu_percent", 0) > 80:
                    logger.warning(f"High CPU usage: {current['cpu_percent']}%")
                if current.get("memory_mb", 0) > 1024:
                    logger.warning(f"High memory usage: {current['memory_mb']}MB")
                    
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")


# Global performance monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


# Decorator for easy performance tracking
def track_performance(func):
    """Decorator to track function performance"""
    monitor = get_performance_monitor()
    return monitor.track_response_time(func)


# Start performance monitoring in background
async def start_performance_monitoring():
    """Start background performance monitoring"""
    monitor = get_performance_monitor()
    settings = get_settings()
    
    if settings.enable_performance_monitoring:
        logger.info("Starting performance monitoring...")
        asyncio.create_task(monitor.periodic_monitoring())
        
        # Log initial optimization status
        optimizations = monitor.check_python_optimizations()
        logger.info(f"Python optimizations active: {optimizations}")


__all__ = [
    "PerformanceMonitor",
    "get_performance_monitor",
    "track_performance",
    "start_performance_monitoring"
]