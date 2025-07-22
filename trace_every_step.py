#!/usr/bin/env python3
"""
Trace Every Step of Workflow Execution
Shows exactly what happens at each node with full details
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.callbacks import BaseCallbackHandler
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
import json
import time

# Import workflow components
from app.workflow import workflow
from app.state.minimal_state import MinimalState

console = Console()

class StepByStepTracer(BaseCallbackHandler):
    """Callback handler that traces every single step"""
    
    def __init__(self):
        self.steps = []
        self.current_step = None
        self.start_time = time.time()
        
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Called when any chain/agent starts"""
        step = {
            "type": "chain_start",
            "name": serialized.get("name", "Unknown"),
            "time": time.time() - self.start_time,
            "inputs": self._clean_inputs(inputs)
        }
        self.steps.append(step)
        self.current_step = step
        
        # Real-time display
        console.print(f"\n[cyan]▶ {step['name']} starting...[/cyan]")
        if "messages" in inputs:
            console.print(f"  Messages: {len(inputs['messages'])}")
        
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called when any chain/agent ends"""
        if self.current_step:
            self.current_step["outputs"] = self._clean_outputs(outputs)
            self.current_step["duration"] = time.time() - self.start_time - self.current_step["time"]
            
            console.print(f"[green]✓ {self.current_step['name']} completed ({self.current_step['duration']:.2f}s)[/green]")
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts"""
        step = {
            "type": "llm_start",
            "model": serialized.get("name", "Unknown"),
            "time": time.time() - self.start_time,
            "prompt_preview": prompts[0][:200] + "..." if prompts else ""
        }
        self.steps.append(step)
        console.print(f"  [yellow]🤖 LLM Call: {step['model']}[/yellow]")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when tool starts"""
        step = {
            "type": "tool_start",
            "tool": serialized.get("name", "Unknown"),
            "time": time.time() - self.start_time,
            "input": input_str[:100] + "..." if len(input_str) > 100 else input_str
        }
        self.steps.append(step)
        console.print(f"  [magenta]🔧 Tool: {step['tool']}[/magenta]")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when tool ends"""
        console.print(f"    [dim]→ {output[:100]}...[/dim]" if len(output) > 100 else f"    [dim]→ {output}[/dim]")
    
    def _clean_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean inputs for display"""
        cleaned = {}
        for key, value in inputs.items():
            if key == "messages":
                cleaned[key] = f"[{len(value)} messages]"
            elif isinstance(value, dict):
                cleaned[key] = {k: v for k, v in value.items() if k not in ["messages"]}
            else:
                cleaned[key] = value
        return cleaned
    
    def _clean_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean outputs for display"""
        if isinstance(outputs, dict):
            return self._clean_inputs(outputs)
        return outputs

async def trace_workflow_execution(message: str, contact_id: str = "trace-test"):
    """Execute workflow with detailed step-by-step tracing"""
    
    console.print(f"\n[bold blue]━━━ STEP-BY-STEP WORKFLOW TRACE ━━━[/bold blue]")
    console.print(Panel(message, title="Input Message", border_style="blue"))
    
    # Create tracer
    tracer = StepByStepTracer()
    
    # Create initial state
    state = {
        "messages": [HumanMessage(content=message)],
        "contact_id": contact_id,
        "thread_id": f"trace-thread-{contact_id}",
        "webhook_data": {
            "body": message,
            "contactId": contact_id,
            "type": "SMS",
            "locationId": "trace-location"
        },
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
        "error": None,
        "remaining_steps": 10,
        "supervisor_complete": False,
        "routing_attempts": 0,
        "interaction_count": 0,
        "escalation_reason": None,
        "response_sent": False,
        "last_sent_message": None,
        "contact_info": None,
        "previous_custom_fields": None,
        "score_reasoning": None,
        "score_history": [],
        "suggested_agent": None
    }
    
    # Configure with callbacks
    config = {
        "configurable": {
            "thread_id": f"trace-thread-{contact_id}"
        },
        "callbacks": [tracer],
        "tags": ["step-trace", "debug"],
        "metadata": {
            "trace_mode": "step-by-step",
            "message": message
        }
    }
    
    console.print("\n[yellow]Starting workflow execution...[/yellow]")
    start_time = time.time()
    
    try:
        # Run workflow
        result = await workflow.ainvoke(state, config)
        
        total_time = time.time() - start_time
        console.print(f"\n[green]✅ Workflow completed in {total_time:.2f}s[/green]")
        
        # Show execution summary
        console.print(f"\n[bold yellow]━━━ EXECUTION SUMMARY ━━━[/bold yellow]")
        
        # Count step types
        step_counts = {}
        for step in tracer.steps:
            step_type = step["type"]
            step_counts[step_type] = step_counts.get(step_type, 0) + 1
        
        console.print(f"Total Steps: {len(tracer.steps)}")
        for step_type, count in step_counts.items():
            console.print(f"  • {step_type}: {count}")
        
        # Show key results
        console.print(f"\n[cyan]Key Results:[/cyan]")
        console.print(f"  • Lead Score: {result.get('lead_score', 0)}/10")
        console.print(f"  • Agent: {result.get('current_agent', 'None')}")
        console.print(f"  • Category: {result.get('lead_category', 'Unknown')}")
        
        if result.get("extracted_data"):
            console.print(f"\n[cyan]Extracted Data:[/cyan]")
            for key, value in result["extracted_data"].items():
                console.print(f"  • {key}: {value}")
        
        # Show final response
        response = None
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                response = msg.content
                break
        
        if response:
            console.print(f"\n[green]Final Response:[/green]")
            console.print(Panel(response, border_style="green"))
        
        # Show detailed step breakdown
        console.print(f"\n[bold yellow]━━━ DETAILED STEP BREAKDOWN ━━━[/bold yellow]")
        
        # Group steps by node
        nodes = {}
        current_node = "initialization"
        
        for step in tracer.steps:
            if step["type"] == "chain_start":
                current_node = step["name"]
                if current_node not in nodes:
                    nodes[current_node] = []
            nodes[current_node].append(step)
        
        # Display each node's activity
        for node_name, node_steps in nodes.items():
            console.print(f"\n[bold cyan]{node_name}:[/bold cyan]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Step", style="green", width=10)
            table.add_column("Type", style="yellow", width=15)
            table.add_column("Details", style="white", width=50)
            table.add_column("Time", style="blue", width=10)
            
            for i, step in enumerate(node_steps, 1):
                details = ""
                if step["type"] == "llm_start":
                    details = f"Model: {step.get('model', 'Unknown')}"
                elif step["type"] == "tool_start":
                    details = f"Tool: {step.get('tool', 'Unknown')}"
                elif step["type"] == "chain_start":
                    details = f"Inputs: {json.dumps(step.get('inputs', {}))[:40]}..."
                
                time_str = f"{step['time']:.2f}s"
                if "duration" in step:
                    time_str += f" ({step['duration']:.2f}s)"
                
                table.add_row(
                    str(i),
                    step["type"],
                    details,
                    time_str
                )
            
            console.print(table)
        
        return result
        
    except Exception as e:
        console.print(f"\n[red]ERROR: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return None

async def main():
    """Main interface for step-by-step tracing"""
    console.print("[bold magenta]🔍 Workflow Step-by-Step Tracer[/bold magenta]")
    console.print("This tool shows every single step of workflow execution")
    console.print("=" * 60)
    
    # Test cases
    test_cases = [
        "Hola, tengo un restaurante",
        "Mi nombre es Juan y tengo una barbería, mi presupuesto es $400",
        "Quiero agendar una cita para mañana"
    ]
    
    console.print("\n[cyan]Test Cases:[/cyan]")
    for i, test in enumerate(test_cases, 1):
        console.print(f"{i}. {test}")
    console.print(f"{len(test_cases) + 1}. Custom message")
    
    choice = input("\nSelect test case (or enter number): ")
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(test_cases):
            message = test_cases[idx]
        else:
            message = input("Enter custom message: ")
    else:
        message = choice
    
    # Run trace
    await trace_workflow_execution(message, f"trace-{datetime.now().timestamp()}")
    
    # Option to run another
    if input("\nRun another trace? (y/n): ").lower() == 'y':
        await main()

if __name__ == "__main__":
    asyncio.run(main())