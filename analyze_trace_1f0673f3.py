#!/usr/bin/env python3
"""
Analyze LangSmith Trace: 1f0673f3-d821-6eb2-b035-0e34cf2537ab
Focus on message flow, agent routing, and response generation
"""

import os
from datetime import datetime
from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

console = Console()

# Initialize client
client = Client()

# Target trace ID
TRACE_ID = "1f0673f3-d821-6eb2-b035-0e34cf2537ab"

def analyze_message_flow(run):
    """Extract and analyze message flow from a run"""
    messages = []
    
    # Check inputs for messages
    if run.inputs and isinstance(run.inputs, dict):
        if "messages" in run.inputs:
            for msg in run.inputs["messages"]:
                # Handle different message formats
                if isinstance(msg, dict):
                    msg_type = msg.get("type", msg.get("message_type", "unknown"))
                    # If type is not found, infer from role
                    if msg_type == "unknown" and "role" in msg:
                        role_map = {"user": "human", "assistant": "ai", "system": "system"}
                        msg_type = role_map.get(msg.get("role", ""), "unknown")
                    
                    messages.append({
                        "source": "input",
                        "type": msg_type,
                        "content": msg.get("content", msg.get("text", "")),
                        "role": msg.get("role", ""),
                        "metadata": msg.get("metadata", {}),
                        "name": msg.get("name", "")
                    })
                elif isinstance(msg, str):
                    messages.append({
                        "source": "input",
                        "type": "human",
                        "content": msg,
                        "role": "user",
                        "metadata": {},
                        "name": ""
                    })
    
    # Check outputs for messages
    if run.outputs and isinstance(run.outputs, dict):
        if "messages" in run.outputs:
            for msg in run.outputs["messages"]:
                if isinstance(msg, dict):
                    msg_type = msg.get("type", msg.get("message_type", "unknown"))
                    # If type is not found, infer from role
                    if msg_type == "unknown" and "role" in msg:
                        role_map = {"user": "human", "assistant": "ai", "system": "system"}
                        msg_type = role_map.get(msg.get("role", ""), "unknown")
                    
                    messages.append({
                        "source": "output",
                        "type": msg_type,
                        "content": msg.get("content", msg.get("text", "")),
                        "role": msg.get("role", ""),
                        "metadata": msg.get("metadata", {}),
                        "name": msg.get("name", "")
                    })
    
    return messages

def analyze_agent_routing(run):
    """Analyze agent routing decisions"""
    routing_info = {}
    
    if run.outputs and isinstance(run.outputs, dict):
        # Check for routing-related fields
        routing_fields = [
            "current_agent", "suggested_agent", "next_agent",
            "lead_score", "score_reasoning", "routing_decision"
        ]
        
        for field in routing_fields:
            if field in run.outputs:
                routing_info[field] = run.outputs[field]
    
    # Check metadata for routing info
    if run.metadata:
        for key, value in run.metadata.items():
            if "agent" in key.lower() or "route" in key.lower():
                routing_info[f"metadata_{key}"] = value
    
    return routing_info

def main():
    """Main analysis function"""
    console.print(f"[bold magenta]🔍 Analyzing LangSmith Trace: {TRACE_ID}[/bold magenta]")
    console.print("=" * 80)
    
    try:
        # Get the main run
        run = client.read_run(TRACE_ID)
        
        # Basic info
        info = f"""
[cyan]Name:[/cyan] {run.name}
[cyan]Status:[/cyan] {run.status}
[cyan]Type:[/cyan] {run.run_type}
[cyan]Start:[/cyan] {run.start_time}
[cyan]End:[/cyan] {run.end_time}
[cyan]Duration:[/cyan] {(run.end_time - run.start_time).total_seconds():.3f}s
[cyan]Total Tokens:[/cyan] {run.total_tokens if hasattr(run, 'total_tokens') else 'N/A'}
[cyan]Error:[/cyan] {run.error or 'None'}
        """
        console.print(Panel(info.strip(), title="Run Information", border_style="blue"))
        
        # Analyze message flow
        console.print("\n[bold yellow]📨 Message Flow Analysis:[/bold yellow]")
        messages = analyze_message_flow(run)
        
        if messages:
            for i, msg in enumerate(messages):
                console.print(f"\n[cyan]Message {i+1} ({msg['source']}):[/cyan]")
                console.print(f"  Type: {msg['type']}")
                if msg['role']:
                    console.print(f"  Role: {msg['role']}")
                if msg['name']:
                    console.print(f"  Agent: [bold green]{msg['name']}[/bold green]")
                if msg['content']:
                    title = f"{msg['type'].upper()} Message"
                    if msg['name']:
                        title = f"{msg['name']} - {msg['type'].upper()}"
                    console.print(Panel(
                        msg['content'][:500] + ("..." if len(msg['content']) > 500 else ""),
                        title=title,
                        border_style="green" if msg['source'] == "output" else "blue"
                    ))
                if msg['metadata']:
                    console.print(f"  Metadata: {json.dumps(msg['metadata'], indent=4)}")
        else:
            console.print("  No messages found in run")
        
        # Analyze agent routing
        console.print("\n[bold yellow]🚦 Agent Routing Analysis:[/bold yellow]")
        routing = analyze_agent_routing(run)
        
        if routing:
            for key, value in routing.items():
                console.print(f"  • {key}: {value}")
        else:
            console.print("  No routing information found")
        
        # Get child runs for detailed workflow analysis
        console.print("\n[bold yellow]🌳 Workflow Execution Tree:[/bold yellow]")
        # Try to get project name from metadata or use default
        project_name = "ghl-langgraph-agent"
        if hasattr(run, 'extra') and run.extra and 'metadata' in run.extra:
            project_name = run.extra['metadata'].get('project_name', project_name)
        
        child_runs = list(client.list_runs(
            project_name=project_name,
            filter=f'eq(parent_run_id, "{TRACE_ID}")',
            limit=100
        ))
        
        if child_runs:
            # Group by node name
            nodes = {}
            agent_responses = {}
            
            for child in child_runs:
                node_name = child.name or "Unknown"
                if node_name not in nodes:
                    nodes[node_name] = []
                nodes[node_name].append(child)
                
                # Look for agent responses
                if "agent" in node_name.lower() and child.outputs:
                    agent_responses[node_name] = child
            
            # Build execution tree
            tree = Tree(f"🌳 {run.name}")
            
            # Sort nodes by execution order
            sorted_nodes = sorted(nodes.items(), key=lambda x: min(r.start_time for r in x[1]))
            
            for node_name, node_runs in sorted_nodes:
                node_style = "cyan"
                if "supervisor" in node_name.lower():
                    node_style = "magenta"
                elif "agent" in node_name.lower():
                    node_style = "green"
                elif "tool" in node_name.lower():
                    node_style = "yellow"
                
                node_branch = tree.add(f"[{node_style}]{node_name}[/{node_style}] ({len(node_runs)} calls)")
                
                for i, child_run in enumerate(node_runs[:3]):  # Show first 3
                    duration = "—"
                    if child_run.end_time and child_run.start_time:
                        duration = f"{(child_run.end_time - child_run.start_time).total_seconds():.3f}s"
                    
                    run_info = f"[{i+1}] {duration}"
                    run_branch = node_branch.add(run_info)
                    
                    # Show key outputs
                    if child_run.outputs:
                        if isinstance(child_run.outputs, dict):
                            # Check for routing decisions
                            if "current_agent" in child_run.outputs:
                                run_branch.add(f"[green]→ Routed to: {child_run.outputs['current_agent']}[/green]")
                            if "messages" in child_run.outputs and child_run.outputs["messages"]:
                                last_msg = child_run.outputs["messages"][-1]
                                if isinstance(last_msg, dict) and "content" in last_msg:
                                    content_preview = last_msg["content"][:100] + "..."
                                    run_branch.add(f"[dim]Response: {content_preview}[/dim]")
                    
                    if child_run.error:
                        run_branch.add(f"[red]Error: {child_run.error[:100]}...[/red]")
                
                if len(node_runs) > 3:
                    node_branch.add(f"[dim]... and {len(node_runs) - 3} more[/dim]")
            
            console.print(tree)
            
            # Show agent responses
            if agent_responses:
                console.print("\n[bold yellow]🤖 Agent Responses:[/bold yellow]")
                for agent_name, agent_run in agent_responses.items():
                    console.print(f"\n[green]{agent_name}:[/green]")
                    
                    # Extract agent's response
                    if agent_run.outputs and isinstance(agent_run.outputs, dict):
                        if "messages" in agent_run.outputs:
                            for msg in agent_run.outputs["messages"]:
                                if isinstance(msg, dict) and msg.get("type") == "ai":
                                    console.print(Panel(
                                        msg.get("content", "No content"),
                                        title=f"{agent_name} Response",
                                        border_style="green"
                                    ))
                                    break
            
            # Summary statistics
            console.print("\n[bold yellow]📊 Execution Summary:[/bold yellow]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Component", style="cyan")
            table.add_column("Executions", style="green")
            table.add_column("Avg Duration", style="blue")
            table.add_column("Errors", style="red")
            
            for node_name, node_runs in nodes.items():
                total_duration = 0
                valid_durations = 0
                errors = 0
                
                for run in node_runs:
                    if run.error:
                        errors += 1
                    if run.end_time and run.start_time:
                        total_duration += (run.end_time - run.start_time).total_seconds()
                        valid_durations += 1
                
                avg_duration = total_duration / valid_durations if valid_durations > 0 else 0
                
                table.add_row(
                    node_name,
                    str(len(node_runs)),
                    f"{avg_duration:.3f}s" if avg_duration > 0 else "—",
                    str(errors) if errors > 0 else "—"
                )
            
            console.print(table)
        
        # Final insights
        console.print("\n[bold yellow]🎯 Key Insights:[/bold yellow]")
        
        # Check if workflow completed
        if run.status == "success":
            console.print("  ✅ Workflow completed successfully")
        else:
            console.print(f"  ❌ Workflow status: {run.status}")
        
        # Check for agent involvement
        if child_runs:
            agents_involved = [n for n in nodes.keys() if "agent" in n.lower()]
            if agents_involved:
                console.print(f"  🤖 Agents involved: {', '.join(agents_involved)}")
            
            # Check for tool usage
            tools_used = [n for n in nodes.keys() if "tool" in n.lower()]
            if tools_used:
                console.print(f"  🔧 Tools used: {', '.join(tools_used)}")
        
        # Show final state if available
        if run.outputs and isinstance(run.outputs, dict):
            if "current_agent" in run.outputs:
                console.print(f"  📍 Final agent: {run.outputs['current_agent']}")
            if "lead_score" in run.outputs:
                console.print(f"  📊 Lead score: {run.outputs['lead_score']}")
        
    except Exception as e:
        console.print(f"[red]Error analyzing trace: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()