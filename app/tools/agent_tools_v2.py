"""
LangGraph tool definitions for GoHighLevel agents - MODERNIZED VERSION
Using latest patterns: InjectedState, InjectedToolCallId, Command objects
"""
from typing import Dict, Any, List, Optional, Literal, Union, Annotated
from datetime import datetime, timedelta
import pytz
import uuid
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState, InjectedStore
from langgraph.types import Command
from langgraph.store.base import BaseStore
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.state.conversation_state import ConversationState
from app.tools.calendar_slots import (
    generate_available_slots, 
    format_slots_for_customer,
    find_matching_slot,
    parse_spanish_datetime
)

logger = get_logger("agent_tools_v2")


# ============ LINEAR FLOW: ESCALATION ONLY ============
@tool
def escalate_to_supervisor(
    reason: Literal["needs_appointment", "needs_qualification", "needs_support", "customer_confused", "wrong_agent"],
    details: str,
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Escalate back to supervisor for re-routing when you cannot handle the request.
    Use this instead of transferring directly to another agent.
    
    Reasons:
    - needs_appointment: Customer wants to schedule but you can't (Maria/Carlos)
    - needs_qualification: Customer needs business assessment but you can't (Maria/Sofia)
    - needs_support: Customer needs general help but you can't (Carlos/Sofia)
    - customer_confused: Customer seems lost or asking unrelated questions
    - wrong_agent: You're not the right agent for this conversation
    """
    current_agent = state.get("current_agent", "unknown")
    routing_attempts = state.get("routing_attempts", 0)
    
    # Prevent infinite escalations
    if routing_attempts >= 2:
        logger.warning(f"Max routing attempts reached ({routing_attempts}), cannot escalate further")
        return Command(
            goto="responder",
            update={
                "messages": state["messages"] + [ToolMessage(
                    content="I apologize, but I'm having trouble routing your request. Please contact support directly.",
                    tool_call_id=tool_call_id
                )],
                "should_end": True
            },
            graph=Command.PARENT
        )
    
    logger.info(f"Agent {current_agent} escalating to supervisor: {reason} - {details}")
    
    tool_message = ToolMessage(
        content=f"Escalating to supervisor for re-routing. Reason: {reason}",
        tool_call_id=tool_call_id
    )
    
    return Command(
        goto="supervisor_brain",
        update={
            "messages": state["messages"] + [tool_message],
            "escalation_reason": reason,
            "escalation_details": details,
            "escalation_from": current_agent,
            "routing_attempts": routing_attempts + 1,
            "needs_rerouting": True
        },
        graph=Command.PARENT
    )


# ============ DEPRECATED: Direct Agent Transfers (Kept for backward compatibility) ============
# These should NOT be used in new code - use escalate_to_supervisor instead
def create_handoff_tool(*, agent_name: str, description: Optional[str] = None):
    """
    DEPRECATED: Creates direct agent-to-agent transfer tools.
    Use escalate_to_supervisor instead for linear flow.
    """
    logger.warning(f"DEPRECATED: create_handoff_tool for {agent_name} - use escalate_to_supervisor instead")
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer to {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[ConversationState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        # Instead of direct transfer, escalate to supervisor
        logger.warning(f"DEPRECATED handoff to {agent_name} - escalating to supervisor instead")
        return escalate_to_supervisor(
            reason="wrong_agent",
            details=f"Legacy transfer attempt to {agent_name}",
            state=state,
            tool_call_id=tool_call_id
        )
    
    return handoff_tool


# Keep these for backward compatibility but they now escalate
transfer_to_sofia = create_handoff_tool(
    agent_name="sofia",
    description="DEPRECATED: Use escalate_to_supervisor with reason='needs_appointment'"
)

transfer_to_carlos = create_handoff_tool(
    agent_name="carlos",
    description="DEPRECATED: Use escalate_to_supervisor with reason='needs_qualification'"
)

transfer_to_maria = create_handoff_tool(
    agent_name="maria",
    description="DEPRECATED: Use escalate_to_supervisor with reason='needs_support'"
)


# ============ CONTACT TOOLS WITH STATE INJECTION ============
@tool
async def get_contact_details_v2(
    contact_id: str,
    state: Annotated[ConversationState, InjectedState]
) -> Dict[str, Any]:
    """
    Get detailed information about a contact from GoHighLevel.
    Now with state injection for context awareness.
    """
    try:
        # Can access state for additional context if needed
        logger.info(f"Agent {state.get('current_agent')} retrieving contact {contact_id}")
        
        contact = await ghl_client.get_contact_details(contact_id)
        if contact:
            return contact
        else:
            return {"error": f"Contact {contact_id} not found"}
    except Exception as e:
        logger.error(f"Error getting contact details: {str(e)}")
        return {"error": str(e)}


@tool
async def update_contact_with_state(
    contact_id: str,
    updates: Dict[str, Any],
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Update contact and return Command to update conversation state
    """
    try:
        result = await ghl_client.update_contact(contact_id, updates)
        
        if result:
            # Update state with the changes
            return Command(
                update={
                    "contact_info": {**state.get("contact_info", {}), **updates},
                    "messages": state["messages"] + [
                        ToolMessage(
                            content=f"Successfully updated contact: {updates}",
                            tool_call_id=tool_call_id
                        )
                    ]
                }
            )
        else:
            return Command(
                update={
                    "error": "Failed to update contact",
                    "messages": state["messages"] + [
                        ToolMessage(
                            content="Failed to update contact information",
                            tool_call_id=tool_call_id,
                            status="error"
                        )
                    ]
                }
            )
    except Exception as e:
        logger.error(f"Error updating contact: {str(e)}")
        return Command(
            update={
                "error": str(e),
                "messages": state["messages"] + [
                    ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call_id,
                        status="error"
                    )
                ]
            }
        )


# ============ APPOINTMENT TOOLS WITH COMMAND PATTERN ============

@tool
async def check_calendar_availability(
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    num_slots: int = 3,
    language: str = "es"
) -> Command:
    """
    Check calendar availability and return formatted available slots
    
    Args:
        num_slots: Number of slots to return (default 3)
        language: Language for formatting (es/en)
    """
    try:
        # Try to get real slots from GHL first
        start_date = datetime.now(pytz.timezone("America/New_York"))
        end_date = start_date + timedelta(days=7)
        
        ghl_slots = await ghl_client.get_calendar_slots(start_date, end_date)
        
        # If no real slots, generate some
        if not ghl_slots:
            logger.info("Using generated slots as GHL API didn't return any")
            slots = generate_available_slots(num_slots=num_slots)
        else:
            # Convert GHL slots to our format
            slots = []
            for ghl_slot in ghl_slots[:num_slots]:
                slots.append({
                    "startTime": datetime.fromisoformat(ghl_slot.get("startTime")),
                    "endTime": datetime.fromisoformat(ghl_slot.get("endTime")),
                    "available": True
                })
        
        # Format slots for customer
        formatted_message = format_slots_for_customer(slots, language)
        
        # Store slots in state for later booking
        return Command(
            update={
                "messages": state["messages"] + [
                    ToolMessage(
                        content=formatted_message,
                        tool_call_id=tool_call_id,
                        status="success",
                        metadata={
                            "slots": [
                                {
                                    "startTime": slot["startTime"].isoformat(),
                                    "endTime": slot["endTime"].isoformat()
                                }
                                for slot in slots
                            ]
                        }
                    )
                ],
                "available_slots": slots  # Store for later use
            }
        )
        
    except Exception as e:
        logger.error(f"Error checking calendar: {str(e)}")
        # Fallback to generated slots
        slots = generate_available_slots(num_slots=num_slots)
        formatted_message = format_slots_for_customer(slots, language)
        
        return Command(
            update={
                "messages": state["messages"] + [
                    ToolMessage(
                        content=formatted_message,
                        tool_call_id=tool_call_id,
                        status="success"
                    )
                ],
                "available_slots": slots
            }
        )


@tool
async def book_appointment_from_confirmation(
    customer_confirmation: str,
    contact_id: str,
    contact_name: str,
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Book appointment based on customer's confirmation
    This tool intelligently parses the customer's response and books the appropriate slot
    
    Args:
        customer_confirmation: Customer's confirmation message (e.g., "mañana a las 3pm está bien")
        contact_id: GHL contact ID
        contact_name: Contact's name for appointment title
    """
    try:
        # Get available slots from state or generate new ones
        available_slots = state.get("available_slots", [])
        if not available_slots:
            logger.info("No slots in state, generating new ones")
            available_slots = generate_available_slots()
        
        # Find matching slot based on customer preference
        selected_slot = find_matching_slot(available_slots, customer_confirmation)
        
        if not selected_slot:
            return Command(
                update={
                    "messages": state["messages"] + [
                        ToolMessage(
                            content="No pude encontrar un horario que coincida. Por favor, elige uno de los horarios disponibles.",
                            tool_call_id=tool_call_id,
                            status="error"
                        )
                    ]
                }
            )
        
        # Create appointment with the selected slot
        result = await ghl_client.create_appointment(
            contact_id=contact_id,
            start_time=selected_slot["startTime"],
            end_time=selected_slot["endTime"],
            title=f"Consulta WhatsApp Automation - {contact_name}",
            timezone="America/New_York"
        )
        
        if result:
            appointment_id = result.get('id', str(uuid.uuid4()))
            
            # Format confirmation message
            formatted_time = format_slot_for_spanish(selected_slot)
            confirmation_msg = f"¡Perfecto! Tu cita está confirmada para {formatted_time}. Te enviaré el enlace de Google Meet a tu email."
            
            return Command(
                update={
                    "appointment_status": "booked",
                    "appointment_id": appointment_id,
                    "appointment_datetime": selected_slot["startTime"].isoformat(),
                    "messages": state["messages"] + [
                        ToolMessage(
                            content=confirmation_msg,
                            tool_call_id=tool_call_id,
                            metadata={
                                "appointment_id": appointment_id,
                                "booked_slot": {
                                    "startTime": selected_slot["startTime"].isoformat(),
                                    "endTime": selected_slot["endTime"].isoformat()
                                }
                            }
                        )
                    ],
                    "should_continue": False
                }
            )
        else:
            return Command(
                update={
                    "messages": state["messages"] + [
                        ToolMessage(
                            content="Hubo un problema al crear la cita. Por favor, intenta nuevamente.",
                            tool_call_id=tool_call_id,
                            status="error"
                        )
                    ]
                }
            )
            
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return Command(
            update={
                "messages": state["messages"] + [
                    ToolMessage(
                        content=f"Error al agendar la cita: {str(e)}",
                        tool_call_id=tool_call_id,
                        status="error"
                    )
                ]
            }
        )


@tool
async def create_appointment_v2(
    contact_id: str,
    start_time: str,
    end_time: str,
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    title: str = "Consultation",
    timezone: str = "America/New_York"
) -> Command:
    """
    Create appointment and return Command to update state and route
    """
    try:
        # Parse times
        tz = pytz.timezone(timezone)
        start_dt = datetime.fromisoformat(start_time).replace(tzinfo=tz)
        end_dt = datetime.fromisoformat(end_time).replace(tzinfo=tz)
        
        result = await ghl_client.create_appointment(
            contact_id, start_dt, end_dt, title, timezone
        )
        
        if result:
            appointment_id = result.get('id', str(uuid.uuid4()))
            
            # Return command to update state and potentially end conversation
            return Command(
                update={
                    "appointment_status": "booked",
                    "appointment_id": appointment_id,
                    "appointment_datetime": start_dt.isoformat(),
                    "messages": state["messages"] + [
                        ToolMessage(
                            content=f"Successfully booked appointment for {start_time}",
                            tool_call_id=tool_call_id
                        )
                    ],
                    "should_continue": False  # Signal to potentially end conversation
                }
            )
        else:
            return Command(
                update={
                    "messages": state["messages"] + [
                        ToolMessage(
                            content="Failed to create appointment",
                            tool_call_id=tool_call_id,
                            status="error"
                        )
                    ]
                }
            )
            
    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}")
        return Command(
            update={
                "error": str(e),
                "messages": state["messages"] + [
                    ToolMessage(
                        content=f"Error creating appointment: {str(e)}",
                        tool_call_id=tool_call_id,
                        status="error"
                    )
                ]
            }
        )


# ============ MEMORY/STORE TOOLS ============
@tool
def save_conversation_context(
    content: str,
    context_type: Literal["preference", "business_info", "goal", "pain_point"],
    *,
    store: Annotated[BaseStore, InjectedStore],
    state: Annotated[ConversationState, InjectedState],
    contact_id: Optional[str] = None
) -> str:
    """
    Save important conversation context to memory store
    """
    contact_id = contact_id or state.get("contact_id", "unknown")
    context_id = str(uuid.uuid4())
    
    store.put(
        (contact_id, "conversation_context"),
        key=context_id,
        value={
            "text": content,
            "type": context_type,
            "agent": state.get("current_agent"),
            "timestamp": datetime.now(pytz.UTC).isoformat()
        }
    )
    
    return f"Saved {context_type} context: {context_id}"


@tool
def search_conversation_history(
    query: str,
    limit: int = 5,
    *,
    store: Annotated[BaseStore, InjectedStore],
    state: Annotated[ConversationState, InjectedState]
) -> List[Dict[str, Any]]:
    """
    Search previous conversation context using semantic search
    """
    contact_id = state.get("contact_id", "unknown")
    
    items = store.search(
        (contact_id, "conversation_context"),
        query=query,
        limit=limit
    )
    
    return [
        {
            "id": item.key,
            "content": item.value["text"],
            "type": item.value.get("type"),
            "agent": item.value.get("agent"),
            "timestamp": item.value.get("timestamp")
        }
        for item in items
    ]


# ============ SPECIALIZED TOOLS WITH DIRECT RETURNS ============
@tool(return_direct=True)
async def book_appointment_and_end(
    contact_id: str,
    appointment_details: Dict[str, Any],
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Book appointment and end conversation directly.
    Using return_direct=True to bypass further agent processing.
    """
    try:
        # Create appointment
        result = await ghl_client.create_appointment(
            contact_id,
            appointment_details["start_time"],
            appointment_details["end_time"],
            appointment_details.get("title", "Consultation"),
            appointment_details.get("timezone", "America/New_York")
        )
        
        if result:
            confirmation = f"""
✅ Appointment Successfully Booked!

📅 Date: {appointment_details['date']}
⏰ Time: {appointment_details['time']}
📍 Type: {appointment_details.get('title', 'Consultation')}
🆔 Confirmation: {result.get('id', 'CONFIRMED')}

You'll receive a confirmation email shortly. Looking forward to speaking with you!

Thank you for choosing Main Outlet Media. Have a great day!
"""
            return confirmation
        else:
            return "I apologize, but I couldn't book the appointment. Please contact support or try again later."
            
    except Exception as e:
        logger.error(f"Error in book_appointment_and_end: {str(e)}")
        return f"An error occurred while booking: {str(e)}. Please contact support."


# ============ TOOL COLLECTIONS FOR AGENTS ============
# Sofia's appointment tools (LINEAR FLOW - no direct transfers)
appointment_tools_v2 = [
    get_contact_details_v2,
    update_contact_with_state,
    create_appointment_v2,
    book_appointment_and_end,
    escalate_to_supervisor,  # Use escalation instead of direct transfers
    save_conversation_context,
    search_conversation_history
]

# Carlos's qualification tools (LINEAR FLOW - no direct transfers)
qualification_tools_v2 = [
    get_contact_details_v2,
    update_contact_with_state,
    escalate_to_supervisor,  # Use escalation instead of direct transfers
    save_conversation_context,
    search_conversation_history
]

# Maria's support tools (LINEAR FLOW - no direct transfers)
support_tools_v2 = [
    get_contact_details_v2,
    escalate_to_supervisor,  # Use escalation instead of direct transfers
    save_conversation_context,
    search_conversation_history
]

# Supervisor tools (just handoffs)
supervisor_tools = [
    transfer_to_sofia,
    transfer_to_carlos,
    transfer_to_maria
]


# Export all tools
__all__ = [
    # LINEAR FLOW: Escalation tool
    "escalate_to_supervisor",
    # DEPRECATED: Legacy handoff tools (now escalate)
    "create_handoff_tool",
    "transfer_to_sofia",
    "transfer_to_carlos", 
    "transfer_to_maria",
    # Tool collections
    "appointment_tools_v2",
    "qualification_tools_v2",
    "support_tools_v2",
    "supervisor_tools",
    # Individual tools
    "get_contact_details_v2",
    "update_contact_with_state",
    "create_appointment_v2",
    "book_appointment_and_end",
    "save_conversation_context",
    "search_conversation_history"
]