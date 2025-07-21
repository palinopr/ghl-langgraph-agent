#!/usr/bin/env python3
"""
CLI Tool to Fetch Traces for Debugging
Makes it easy to get traces and share with Claude
"""
import sys
import json
import argparse
import requests
from datetime import datetime
from typing import Optional

# Default API URL
DEFAULT_API_URL = "http://localhost:8000"


def fetch_trace(trace_id: str, api_url: str) -> dict:
    """Fetch a specific trace by ID"""
    response = requests.get(f"{api_url}/debug/trace/{trace_id}")
    response.raise_for_status()
    return response.json()


def fetch_last_trace(api_url: str) -> dict:
    """Fetch the most recent trace"""
    response = requests.get(f"{api_url}/debug/last-trace")
    response.raise_for_status()
    return response.json()


def fetch_last_error(api_url: str) -> dict:
    """Fetch the most recent error trace"""
    response = requests.get(f"{api_url}/debug/last-error")
    response.raise_for_status()
    return response.json()


def fetch_traces_for_contact(contact_id: str, api_url: str, limit: int = 10) -> dict:
    """Fetch traces for a specific contact"""
    response = requests.get(f"{api_url}/debug/traces", params={
        "contact_id": contact_id,
        "limit": limit
    })
    response.raise_for_status()
    return response.json()


def fetch_active_traces(api_url: str) -> dict:
    """Fetch currently active traces"""
    response = requests.get(f"{api_url}/debug/active")
    response.raise_for_status()
    return response.json()


def export_trace(trace_id: str, api_url: str) -> dict:
    """Export trace in debugging format"""
    response = requests.get(f"{api_url}/debug/trace/{trace_id}/export")
    response.raise_for_status()
    return response.json()


def format_timeline(timeline: list) -> str:
    """Format timeline for display"""
    return "\n".join(timeline)


def format_trace_summary(trace: dict) -> str:
    """Format trace summary for display"""
    summary = f"""
TRACE SUMMARY
=============
Trace ID: {trace.get('trace_id', 'unknown')}
Contact: {trace.get('contact_id', 'unknown')}
Status: {trace.get('status', 'unknown')}
Duration: {trace.get('duration_ms', 'N/A')}ms

Message: {trace.get('webhook_data', {}).get('message', 'N/A')}

Timeline:
{format_timeline(trace.get('timeline', []))}
"""
    
    if trace.get('errors'):
        summary += f"\n\nERRORS ({len(trace['errors'])}):\n"
        for error in trace['errors']:
            summary += f"- [{error['timestamp']}] {error['location']}: {error['message']}\n"
    
    if trace.get('debug_hints'):
        summary += f"\n\nDEBUG HINTS:\n"
        for hint in trace['debug_hints']:
            summary += f"- {hint}\n"
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="Fetch traces for debugging")
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Get specific trace
    trace_parser = subparsers.add_parser("trace", help="Get a specific trace")
    trace_parser.add_argument("trace_id", help="Trace ID to fetch")
    trace_parser.add_argument("--export", action="store_true", help="Export in debugging format")
    
    # Get last trace
    last_parser = subparsers.add_parser("last", help="Get the last trace")
    last_parser.add_argument("--export", action="store_true", help="Export in debugging format")
    
    # Get last error
    error_parser = subparsers.add_parser("error", help="Get the last error trace")
    
    # Get traces for contact
    contact_parser = subparsers.add_parser("contact", help="Get traces for a contact")
    contact_parser.add_argument("contact_id", help="Contact ID")
    contact_parser.add_argument("--limit", type=int, default=10, help="Number of traces")
    
    # Get active traces
    active_parser = subparsers.add_parser("active", help="Get active traces")
    
    # List all traces
    list_parser = subparsers.add_parser("list", help="List recent traces")
    list_parser.add_argument("--limit", type=int, default=20, help="Number of traces")
    list_parser.add_argument("--status", choices=["completed", "error"], help="Filter by status")
    
    # Quick debug
    debug_parser = subparsers.add_parser("debug", help="Quick debug for contact")
    debug_parser.add_argument("contact_id", help="Contact ID to debug")
    
    # Global options
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API URL")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    
    args = parser.parse_args()
    
    # Use the API URL from args
    api_url = args.api_url
    
    try:
        # Execute command
        if args.command == "trace":
            if args.export:
                result = export_trace(args.trace_id, api_url)
            else:
                result = fetch_trace(args.trace_id, api_url)
        
        elif args.command == "last":
            trace = fetch_last_trace(api_url)
            if args.export:
                result = export_trace(trace['trace_id'], api_url)
            else:
                result = trace
        
        elif args.command == "error":
            result = fetch_last_error(api_url)
        
        elif args.command == "contact":
            result = fetch_traces_for_contact(args.contact_id, api_url, args.limit)
        
        elif args.command == "active":
            result = fetch_active_traces(api_url)
        
        elif args.command == "list":
            response = requests.get(f"{api_url}/debug/traces", params={
                "limit": args.limit,
                "status": args.status
            })
            response.raise_for_status()
            result = response.json()
        
        elif args.command == "debug":
            response = requests.get(f"{api_url}/debug/quick-debug/{args.contact_id}")
            response.raise_for_status()
            result = response.json()
        
        else:
            parser.print_help()
            return
        
        # Output result
        if args.raw:
            print(json.dumps(result))
        elif args.pretty:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # Format based on command
            if args.command in ["trace", "last", "error"] and isinstance(result, dict) and "trace_id" in result:
                print(format_trace_summary(result))
            elif args.command == "list":
                print(f"\nFound {result['count']} traces:\n")
                for trace in result['traces']:
                    print(f"- [{trace['started_at']}] {trace['trace_id']}")
                    print(f"  Contact: {trace['contact_id']}, Status: {trace['status']}")
                    print(f"  Message: {trace['message']}")
                    if trace['errors'] > 0:
                        print(f"  ⚠️  {trace['errors']} errors")
                    print()
            elif args.command == "contact":
                print(f"\nTraces for contact {args.contact_id}:\n")
                for trace in result['traces']:
                    print(f"- {trace['trace_id']} ({trace['status']})")
                    print(f"  {trace['started_at']}")
                    print(f"  Duration: {trace.get('duration_ms', 'N/A')}ms")
                    print()
            elif args.command == "active":
                print(f"\n{result['count']} active traces:\n")
                for trace in result['traces']:
                    print(f"- {trace['trace_id']}")
                    print(f"  Started: {trace['started_at']}")
                    print(f"  Events: {trace['events_so_far']}")
                    print()
            elif args.command == "debug":
                print(f"\nDebug info for {args.contact_id}:\n")
                print(f"Recent traces: {result['recent_traces']}")
                print("\nLatest trace:")
                print(format_trace_summary(result['latest_trace']))
                print("\nExport commands:")
                for cmd, url in result['export_commands'].items():
                    print(f"- {cmd}: {url}")
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to connect to API at {api_url}")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()