"""
Simplified Supervisor Brain - Direct implementation
"""
from typing import Dict, Any, Literal
from datetime import datetime
from langchain_core.messages import AIMessage
from app.tools.ghl_client import GHLClient
from app.constants import FIELD_MAPPINGS
from app.utils.simple_logger import get_logger
from app.utils.data_validation import validate_response, extract_valid_data, validate_budget_confirmation
import re

logger = get_logger("supervisor_brain_simple")


async def supervisor_brain_simple_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple supervisor that analyzes, scores, updates GHL, and routes
    """
    contact_id = state.get("contact_id")
    logger.info(f"Supervisor analyzing lead {contact_id}")
    
    try:
        # 1. ANALYZE LEAD
        # Get the latest user message (not the receptionist summary)
        current_message = ""
        messages = state.get("messages", [])
        
        # Look for the latest human message
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                current_message = msg.content
                break
                
        # Fallback to first message if no human message found
        if not current_message and messages and len(messages) > 0:
            if hasattr(messages[0], 'content'):
                current_message = messages[0].content
        
        logger.info(f"Analyzing message: {current_message}")
                
        contact_info = state.get("contact_info", {})
        previous_fields = state.get("previous_custom_fields", {})
        
        logger.info(f"State keys: {list(state.keys())}")
        logger.info(f"Previous custom fields from state: {previous_fields}")
        
        # Previous values - score might be a string "1" not int
        try:
            previous_score = int(previous_fields.get("score", "0") or "0")
        except:
            previous_score = 0
        # Name comes from contact_info, not custom fields
        previous_name = contact_info.get("firstName", "") or previous_fields.get("name", "")
        previous_business = previous_fields.get("business_type", "NO_MENCIONADO") 
        if not previous_business or previous_business == "":
            previous_business = "NO_MENCIONADO"
        previous_budget = previous_fields.get("budget", "")
        
        logger.info(f"Previous values - Score: {previous_score}, Name: {previous_name}, Business: {previous_business}, Budget: {previous_budget}")
        
        # Extract new information
        extracted = {"name": None, "business_type": None, "budget": None}
        
        # Look for restaurant mention
        if any(word in current_message.lower() for word in ["restaurante", "restaurant", "comida"]):
            extracted["business_type"] = "restaurante"
            logger.info("Found restaurant mention!")
            
        # Look for name patterns with validation
        name_patterns = [
            r'mi nombre es\s+([A-Za-zÀ-ÿ\s]+)',
            r'me llamo\s+([A-Za-zÀ-ÿ\s]+)',
            r'soy\s+([A-Za-zÀ-ÿ\s]+)',
            r'my name is\s+([A-Za-z\s]+)',
            r"i'm\s+([A-Za-z\s]+)",
            r'i am\s+([A-Za-z\s]+)'
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, current_message, re.IGNORECASE)
            if name_match:
                potential_name = name_match.group(1).strip()
                # Validate it's actually a name
                validated_name = extract_valid_data(potential_name, 'name')
                if validated_name:
                    extracted["name"] = validated_name
                    logger.info(f"Found and validated name: {extracted['name']}")
                    break
            
        # Look for budget patterns
        budget_match = re.search(r'\$?(\d+)\s*(?:al mes|mensuales|/mes|monthly|per month)?', current_message, re.IGNORECASE)
        if budget_match:
            extracted["budget"] = f"{budget_match.group(1)}/month"
        
        # Also check for budget confirmation responses
        if not extracted["budget"] and previous_score >= 5:  # Only check confirmations after initial qualification
            if validate_budget_confirmation(current_message, previous_score):
                extracted["budget"] = "300+/month"  # Confirmed minimum budget
                logger.info("Detected budget confirmation")
        
        # Calculate score
        score = 1  # Base score for any message
        
        # Only add points for information mentioned in THIS message
        if extracted["name"]:
            score += 2  # Name mentioned in current message
        elif previous_name:
            # Already have name from before, no extra points
            pass
            
        if extracted["business_type"]:
            score += 1  # Business mentioned in current message
        elif previous_business and previous_business != "NO_MENCIONADO":
            # Already have business from before, no extra points
            pass
            
        if extracted["budget"]:
            score += 2  # Budget mentioned in current message
            if "300" in str(extracted["budget"]) or "500" in str(extracted["budget"]):
                score += 1  # High budget
        elif previous_budget:
            # Already have budget from before, no extra points
            pass
        
        # Accumulate with previous score (never decrease)
        final_score = previous_score + score
        
        # Final values for GHL update
        final_name = extracted["name"] or previous_name
        final_business = extracted["business_type"] or previous_business
        final_budget = extracted["budget"] or previous_budget
        
        logger.info(f"Lead analysis: Score {previous_score} -> {final_score}")
        logger.info(f"Extracted - Name: {extracted['name']}, Business: {extracted['business_type']}, Budget: {extracted['budget']}")
        
        # 2. UPDATE GHL
        ghl_client = GHLClient()
        
        # Prepare custom fields - GHL expects array format with id/value pairs
        custom_fields = [
            {"id": FIELD_MAPPINGS["score"], "value": str(final_score)}
        ]
        
        if final_business and final_business != "NO_MENCIONADO":
            custom_fields.append({
                "id": FIELD_MAPPINGS["business_type"],
                "value": final_business
            })
            
        if final_budget:
            custom_fields.append({
                "id": FIELD_MAPPINGS["budget"],
                "value": final_budget
            })
            
        if final_name:
            custom_fields.append({
                "id": FIELD_MAPPINGS["name"],
                "value": final_name
            })
            
        # Update contact
        contact_updates = {"customFields": custom_fields}  # GHL API uses plural 'customFields'
        await ghl_client.update_contact(contact_id, contact_updates)
        
        # Update tags
        tags = []
        if final_score >= 8:
            tags = ["hot-lead", "ready-to-buy"]
        elif final_score >= 5:
            tags = ["warm-lead", "needs-qualification"]
        else:
            tags = ["cold-lead", "needs-nurturing"]
            
        await ghl_client.add_tags(contact_id, tags)
        
        # Create note
        note = f"""Lead Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}
Score: {final_score}/10
Business: {final_business}
Changes: Score updated from {previous_score} to {final_score}
"""
        await ghl_client.create_note(contact_id, note)
        
        logger.info(f"GHL updated: Score={final_score}, Tags={tags}")
        
        # 3. ROUTING DECISION
        # Check if this is an escalation (re-routing)
        if state.get("needs_rerouting") and state.get("escalation_reason"):
            escalation_from = state.get("escalation_from", "unknown")
            escalation_reason = state.get("escalation_reason")
            
            logger.info(f"Handling escalation from {escalation_from}: {escalation_reason}")
            
            # Route based on escalation reason
            if escalation_reason == "needs_appointment":
                next_agent = "sofia"
                routing_reason = f"Escalation: Customer needs appointment booking"
            elif escalation_reason == "needs_qualification":
                next_agent = "carlos"
                routing_reason = f"Escalation: Customer needs business qualification"
            elif escalation_reason == "needs_support":
                next_agent = "maria"
                routing_reason = f"Escalation: Customer needs general support"
            else:
                # Re-analyze based on score
                if final_score >= 8:
                    next_agent = "sofia"
                elif final_score >= 5:
                    next_agent = "carlos"
                else:
                    next_agent = "maria"
                routing_reason = f"Escalation: Re-routed based on score {final_score}"
            
            # Don't route back to the same agent
            if next_agent == escalation_from:
                logger.warning(f"Avoiding circular routing back to {escalation_from}")
                # Pick next best agent
                if escalation_from == "maria" and final_score >= 5:
                    next_agent = "carlos"
                elif escalation_from == "carlos" and final_score >= 8:
                    next_agent = "sofia"
                elif escalation_from == "sofia" and final_score < 8:
                    next_agent = "carlos" if final_score >= 5 else "maria"
                routing_reason += f" (avoiding circular route to {escalation_from})"
        else:
            # Normal first-time routing based on score
            if final_score >= 8:
                # Hot lead - go straight to Sofia for closing
                next_agent = "sofia"
                routing_reason = "Hot lead ready for appointment (score 8+)"
            elif final_score >= 5:
                # Warm lead - needs qualification
                next_agent = "carlos"
                routing_reason = "Warm lead needs qualification"
            else:
                # Cold lead - needs nurturing
                next_agent = "maria"
                routing_reason = "Cold lead needs nurturing"
            
        logger.info(f"Routing to {next_agent}: {routing_reason}")
        
        # Create summary message
        summary = f"""
SUPERVISOR ANALYSIS COMPLETE:
- Score: {final_score}/10
- Business: {final_business}
- Routing to: {next_agent.upper()}
- Reason: {routing_reason}
"""
        
        summary_msg = AIMessage(
            content=summary,
            name="supervisor_brain"
        )
        
        # Return updates
        result = {
            "messages": state.get("messages", []) + [summary_msg],
            "lead_score": final_score,
            "extracted_data": {
                "name": final_name,
                "business_type": final_business,
                "budget": final_budget
            },
            "next_agent": next_agent,
            "supervisor_complete": True,
            "interaction_count": state.get("interaction_count", 0) + 1,
            "current_agent": next_agent  # Set current agent for routing
        }
        
        # Clear escalation flags if this was a re-routing
        if state.get("needs_rerouting"):
            result["needs_rerouting"] = False
            result["escalation_reason"] = None
            result["escalation_details"] = None
            result["escalation_from"] = None
            
        return result
        
    except Exception as e:
        logger.error(f"Supervisor error: {str(e)}", exc_info=True)
        return {
            "next_agent": "maria",
            "error": str(e),
            "supervisor_complete": True,
            "interaction_count": state.get("interaction_count", 0) + 1
        }