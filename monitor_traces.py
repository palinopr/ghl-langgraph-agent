#!/usr/bin/env python3
"""
Real-time Trace Monitor - Catch message duplication issues immediately
"""
import os
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any
from langsmith import Client
from app.utils.debug_helpers import trace_message_flow
from app.utils.simple_logger import get_logger

logger = get_logger("trace_monitor")


class TraceMonitor:
    """Monitor LangSmith traces for issues in real-time"""
    
    def __init__(self, project_name: str = "ghl-langgraph-agent"):
        self.client = Client()
        self.project_name = project_name
        self.seen_traces = set()
        self.issue_count = 0
        
    def analyze_trace(self, trace_id: str) -> Dict[str, Any]:
        """Analyze a single trace for issues"""
        try:
            run = self.client.read_run(trace_id)
            
            # Get child runs (nodes)
            child_runs = list(self.client.list_runs(
                project_name=self.project_name,
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=50
            ))
            
            # Sort by start time
            child_runs.sort(key=lambda x: x.start_time)
            
            # Build node data for analysis
            nodes = []
            total_messages = 0
            has_errors = False
            
            for child in child_runs:
                input_msgs = 0
                output_msgs = 0
                
                # Count input messages
                if child.inputs and "messages" in child.inputs:
                    input_msgs = len(child.inputs["messages"])
                
                # Count output messages
                if child.outputs and "messages" in child.outputs:
                    output_msgs = len(child.outputs["messages"])
                
                # Check for errors
                if child.error or (child.outputs and "Error" in str(child.outputs)):
                    has_errors = True
                
                nodes.append({
                    "name": child.name,
                    "input_messages": input_msgs,
                    "output_messages": output_msgs,
                    "duration": (child.end_time - child.start_time).total_seconds() if child.end_time else 0,
                    "error": bool(child.error)
                })
                
                total_messages = max(total_messages, output_msgs)
            
            # Detect issues
            issues = []
            
            # Check for exponential growth
            if len(nodes) > 0 and total_messages > len(nodes) * 3:
                issues.append(f"Message explosion: {total_messages} messages after {len(nodes)} nodes")
            
            # Check for duplication pattern
            message_counts = [n["output_messages"] for n in nodes if n["output_messages"] > 0]
            if len(message_counts) >= 3:
                # Check if each node doubles messages (1->2->4->8)
                is_doubling = all(
                    message_counts[i] >= message_counts[i-1] * 1.5 
                    for i in range(1, len(message_counts))
                )
                if is_doubling:
                    issues.append("Exponential duplication pattern detected")
            
            # Check for errors
            if has_errors:
                error_nodes = [n["name"] for n in nodes if n["error"]]
                issues.append(f"Errors in nodes: {', '.join(error_nodes)}")
            
            return {
                "trace_id": trace_id,
                "timestamp": run.start_time,
                "total_messages": total_messages,
                "node_count": len(nodes),
                "has_errors": has_errors,
                "issues": issues,
                "nodes": nodes
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze trace {trace_id}: {e}")
            return {
                "trace_id": trace_id,
                "error": str(e),
                "issues": ["Failed to analyze trace"]
            }
    
    async def monitor_continuous(self, check_interval: int = 30):
        """Continuously monitor for new traces"""
        print(f"\n{'='*80}")
        print(f"LANGGRAPH TRACE MONITOR - {self.project_name}")
        print(f"{'='*80}")
        print(f"Checking every {check_interval} seconds for issues...")
        print(f"Press Ctrl+C to stop\n")
        
        while True:
            try:
                # Get recent runs
                recent_runs = list(self.client.list_runs(
                    project_name=self.project_name,
                    limit=10,
                    order_by=["start_time"],
                    error=False  # Only successful runs
                ))
                
                # Check new traces
                for run in recent_runs:
                    if run.id not in self.seen_traces:
                        self.seen_traces.add(run.id)
                        
                        # Analyze trace
                        analysis = self.analyze_trace(run.id)
                        
                        # Report issues
                        if analysis.get("issues"):
                            self.issue_count += 1
                            self.report_issue(analysis)
                        elif analysis.get("total_messages", 0) > 10:
                            # Warn about high message count even without specific issues
                            print(f"⚠️  High message count: {analysis['total_messages']} in trace {run.id[:8]}")
                
                # Status update
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Monitored {len(self.seen_traces)} traces, found {self.issue_count} issues", end="", flush=True)
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped.")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(check_interval)
    
    def report_issue(self, analysis: Dict[str, Any]):
        """Report a detected issue"""
        print(f"\n\n{'='*80}")
        print(f"🚨 ISSUE DETECTED - Trace: {analysis['trace_id'][:8]}")
        print(f"{'='*80}")
        print(f"Time: {analysis.get('timestamp', 'Unknown')}")
        print(f"Total Messages: {analysis.get('total_messages', 'Unknown')}")
        print(f"Issues:")
        for issue in analysis.get("issues", []):
            print(f"  - {issue}")
        
        # Show message flow
        if analysis.get("nodes"):
            print("\nMessage Flow:")
            trace_message_flow({"nodes": analysis["nodes"]})
        
        print(f"\n📊 View trace: https://smith.langchain.com/public/{analysis['trace_id']}/r")
        print(f"{'='*80}\n")
    
    def generate_report(self):
        """Generate a summary report"""
        print(f"\n{'='*80}")
        print("MONITORING SUMMARY")
        print(f"{'='*80}")
        print(f"Total traces monitored: {len(self.seen_traces)}")
        print(f"Issues found: {self.issue_count}")
        if self.issue_count > 0:
            print(f"Issue rate: {self.issue_count / len(self.seen_traces) * 100:.1f}%")


async def main():
    """Main monitoring function"""
    # Check for LangSmith API key
    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("❌ LANGCHAIN_API_KEY not set. Please set it to use trace monitoring.")
        return
    
    # Create monitor
    monitor = TraceMonitor()
    
    try:
        # Run continuous monitoring
        await monitor.monitor_continuous(check_interval=30)
    finally:
        # Generate report
        monitor.generate_report()


if __name__ == "__main__":
    asyncio.run(main())