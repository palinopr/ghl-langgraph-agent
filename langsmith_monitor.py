#!/usr/bin/env python3
"""
LangSmith Monitoring Script for LangGraph Platform Deployments

This script demonstrates how to use the LangSmith Python SDK to:
- Check deployment status
- View logs and traces
- Monitor LangGraph Platform deployments
- Access metrics programmatically
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

try:
    from langsmith import Client
    from langsmith.schemas import Run, Dataset, Example
except ImportError:
    print("Error: langsmith package not installed. Run: pip install langsmith")
    sys.exit(1)


class LangSmithMonitor:
    """Monitor LangGraph Platform deployments using LangSmith API"""
    
    def __init__(self, api_key: Optional[str] = None, project_name: Optional[str] = None):
        """
        Initialize LangSmith client
        
        Args:
            api_key: LangSmith API key (defaults to LANGCHAIN_API_KEY env var)
            project_name: Project name (defaults to LANGCHAIN_PROJECT env var)
        """
        self.api_key = api_key or os.getenv("LANGCHAIN_API_KEY")
        self.project_name = project_name or os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-migration")
        
        if not self.api_key:
            raise ValueError("LANGCHAIN_API_KEY environment variable or api_key parameter required")
        
        # Initialize client
        self.client = Client(api_key=self.api_key)
        print(f"Connected to LangSmith - Project: {self.project_name}")
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all available projects"""
        try:
            projects = list(self.client.list_projects())
            return [{"name": p.name, "id": p.id} for p in projects]
        except Exception as e:
            print(f"Error listing projects: {e}")
            return []
    
    def get_recent_runs(self, hours: int = 24, limit: int = 100) -> List[Run]:
        """
        Get recent runs from the project
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of runs to return
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            runs = list(self.client.list_runs(
                project_name=self.project_name,
                start_time=start_time,
                limit=limit
            ))
            
            return runs
        except Exception as e:
            print(f"Error fetching runs: {e}")
            return []
    
    def get_run_details(self, run_id: str) -> Optional[Run]:
        """Get detailed information about a specific run"""
        try:
            return self.client.read_run(run_id)
        except Exception as e:
            print(f"Error fetching run details: {e}")
            return None
    
    def get_deployment_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate deployment metrics from recent runs
        
        Args:
            hours: Number of hours to analyze
        """
        runs = self.get_recent_runs(hours=hours)
        
        if not runs:
            return {"error": "No runs found"}
        
        # Calculate metrics
        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r.status == "success")
        failed_runs = sum(1 for r in runs if r.error)
        
        # Calculate latencies
        latencies = []
        for run in runs:
            if run.end_time and run.start_time:
                latency = (run.end_time - run.start_time).total_seconds()
                latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # Get error messages
        errors = [
            {
                "run_id": str(run.id),
                "error": run.error,
                "timestamp": run.start_time.isoformat() if run.start_time else None
            }
            for run in runs if run.error
        ]
        
        return {
            "time_range_hours": hours,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
            "average_latency_seconds": round(avg_latency, 2),
            "recent_errors": errors[:10]  # Last 10 errors
        }
    
    def monitor_live(self, interval_seconds: int = 60):
        """
        Monitor deployment in real-time
        
        Args:
            interval_seconds: Polling interval
        """
        import time
        
        print(f"Starting live monitoring (refresh every {interval_seconds}s)...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Clear screen (works on Unix/Linux/Mac)
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Print header
                print(f"=== LangSmith Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
                print(f"Project: {self.project_name}\n")
                
                # Get metrics
                metrics = self.get_deployment_metrics(hours=1)
                
                # Display metrics
                print("Last Hour Metrics:")
                print(f"  Total Runs: {metrics.get('total_runs', 0)}")
                print(f"  Success Rate: {metrics.get('success_rate', 0):.1f}%")
                print(f"  Average Latency: {metrics.get('average_latency_seconds', 0):.2f}s")
                print(f"  Failed Runs: {metrics.get('failed_runs', 0)}")
                
                # Show recent errors if any
                errors = metrics.get('recent_errors', [])
                if errors:
                    print("\nRecent Errors:")
                    for error in errors[:5]:
                        print(f"  - {error['timestamp']}: {error['error'][:100]}...")
                
                # Show recent runs
                recent_runs = self.get_recent_runs(hours=1, limit=10)
                if recent_runs:
                    print("\nRecent Runs:")
                    for run in recent_runs[:5]:
                        status = "✓" if run.status == "success" else "✗"
                        print(f"  {status} {run.name} - {run.start_time.strftime('%H:%M:%S')}")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    
    def export_logs(self, hours: int = 24, output_file: str = "langsmith_logs.json"):
        """
        Export logs to a file
        
        Args:
            hours: Number of hours to export
            output_file: Output filename
        """
        runs = self.get_recent_runs(hours=hours)
        
        logs = []
        for run in runs:
            log_entry = {
                "run_id": str(run.id),
                "name": run.name,
                "status": run.status,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "error": run.error,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "metadata": run.extra
            }
            logs.append(log_entry)
        
        with open(output_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"Exported {len(logs)} log entries to {output_file}")


def main():
    """Main function with CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor LangGraph Platform deployments with LangSmith")
    parser.add_argument("--project", help="Project name (defaults to LANGCHAIN_PROJECT env var)")
    parser.add_argument("--api-key", help="LangSmith API key (defaults to LANGCHAIN_API_KEY env var)")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List projects command
    subparsers.add_parser("list-projects", help="List all available projects")
    
    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show deployment metrics")
    metrics_parser.add_argument("--hours", type=int, default=24, help="Hours to analyze (default: 24)")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Live monitoring")
    monitor_parser.add_argument("--interval", type=int, default=60, help="Refresh interval in seconds")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export logs to file")
    export_parser.add_argument("--hours", type=int, default=24, help="Hours to export (default: 24)")
    export_parser.add_argument("--output", default="langsmith_logs.json", help="Output file")
    
    # Recent runs command
    runs_parser = subparsers.add_parser("runs", help="Show recent runs")
    runs_parser.add_argument("--hours", type=int, default=1, help="Hours to look back (default: 1)")
    runs_parser.add_argument("--limit", type=int, default=20, help="Max runs to show (default: 20)")
    
    args = parser.parse_args()
    
    # Initialize monitor
    try:
        monitor = LangSmithMonitor(api_key=args.api_key, project_name=args.project)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Execute command
    if args.command == "list-projects":
        projects = monitor.list_projects()
        print("Available Projects:")
        for project in projects:
            print(f"  - {project['name']} (ID: {project['id']})")
    
    elif args.command == "metrics":
        metrics = monitor.get_deployment_metrics(hours=args.hours)
        print(f"\nMetrics for last {args.hours} hours:")
        print(json.dumps(metrics, indent=2))
    
    elif args.command == "monitor":
        monitor.monitor_live(interval_seconds=args.interval)
    
    elif args.command == "export":
        monitor.export_logs(hours=args.hours, output_file=args.output)
    
    elif args.command == "runs":
        runs = monitor.get_recent_runs(hours=args.hours, limit=args.limit)
        print(f"\nRecent runs (last {args.hours} hour(s)):")
        for run in runs:
            status = "SUCCESS" if run.status == "success" else "FAILED"
            timestamp = run.start_time.strftime('%Y-%m-%d %H:%M:%S') if run.start_time else "N/A"
            print(f"  [{status}] {run.name} - {timestamp}")
            if run.error:
                print(f"    Error: {run.error[:100]}...")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()