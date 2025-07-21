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
from app.utils.debug_logger import DebugLogger, TimingContext, debug_async
from app.utils.deployment_check import log_deployment_info
import re

logger = get_logger("supervisor_brain_simple")

# Log deployment info once at module load
log_deployment_info()


@debug_async("SUPERVISOR_BRAIN")
async def supervisor_brain_simple_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple supervisor that analyzes, scores, updates GHL, and routes
    """
    contact_id = state.get("contact_id")
    logger.info(f"Supervisor analyzing lead {contact_id}")
    
    try:
        # 1. ANALYZE LEAD
        # Get the latest user message from webhook data (the actual incoming message)
        current_message = ""
        
        # First try to get from webhook data (the actual new message)
        webhook_data = state.get("webhook_data", {})
        if webhook_data and webhook_data.get("message"):
            current_message = webhook_data["message"]
            logger.info(f"Using message from webhook: {current_message}")
        else:
            # Fallback: Find the FIRST human message (which is the new one)
            # When called from LangGraph API, the first message is the user's input
            messages = state.get("messages", [])
            
            # Look for the first human message without ghl_history source
            for msg in messages:
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                    # Check if it's NOT from history
                    additional_kwargs = getattr(msg, 'additional_kwargs', {})
                    if additional_kwargs.get('source') != 'ghl_history':
                        current_message = msg.content
                        logger.info(f"Found user message: {current_message}")
                        break
                    
            # If no non-history human message, try the very first message
            if not current_message and messages and len(messages) > 0:
                if hasattr(messages[0], 'content') and hasattr(messages[0], '__class__'):
                    if messages[0].__class__.__name__ == 'HumanMessage':
                        current_message = messages[0].content
                        logger.info(f"Using first message as fallback: {current_message}")
        
        logger.info(f"Analyzing message: {current_message}")
                
        contact_info = state.get("contact_info", {})
        previous_fields = state.get("previous_custom_fields", {})
        
        # ALSO check if we have extracted_data from previous iterations
        existing_extracted = state.get("extracted_data", {})
        
        logger.info(f"State keys: {list(state.keys())}")
        logger.info(f"Previous custom fields from state: {previous_fields}")
        logger.info(f"Existing extracted data from state: {existing_extracted}")
        
        # Previous values - check multiple sources
        # 1. First check existing extracted data
        # 2. Then check previous custom fields
        # 3. Finally check contact info
        
        # Score - maintain the highest score seen
        try:
            score_from_extracted = int(existing_extracted.get("score", 0))
            score_from_fields = int(previous_fields.get("score", "0") or "0")
            score_from_state = int(state.get("lead_score", 0))
            previous_score = max(score_from_extracted, score_from_fields, score_from_state)
        except:
            previous_score = 0
            
        # Name - check multiple sources
        previous_name = (
            existing_extracted.get("name", "") or
            contact_info.get("firstName", "") or 
            previous_fields.get("name", "")
        )
        
        # Business - check multiple sources
        previous_business = (
            existing_extracted.get("business_type", "") or
            previous_fields.get("business_type", "")
        )
        if not previous_business or previous_business == "":
            previous_business = "NO_MENCIONADO"
            
        # Budget - check multiple sources
        previous_budget = (
            existing_extracted.get("budget", "") or
            previous_fields.get("budget", "")
        )
        
        logger.info(f"Previous values - Score: {previous_score}, Name: {previous_name}, Business: {previous_business}, Budget: {previous_budget}")
        
        # Extract new information
        extracted = {"name": None, "business_type": None, "budget": None}
        
        # Enhanced business extraction
        logger.info(f"🔍 Attempting to extract business from: '{current_message}'")
        
        # Direct business type matches
        direct_business_words = [
            "restaurante", "restaurant", "tienda", "salon", "salón", 
            "barbería", "barberia", "clinica", "clínica", "consultorio",
            "agencia", "hotel", "gym", "gimnasio", "spa", "café", "cafe",
            "pizzería", "pizzeria", "panadería", "panaderia", "farmacia",
            "comida", "negocio"
        ]
        
        message_lower = current_message.lower().strip()
        
        # Check direct matches first
        for business in direct_business_words:
            if business in message_lower:
                extracted["business_type"] = business
                logger.info(f"✅ Found business type via direct match: {business}")
                break
        
        # If not found, try pattern matching
        if not extracted["business_type"]:
            # Handle single-word responses (like just "Restaurante")
            if len(message_lower.split()) <= 2 and message_lower.strip().rstrip('.,!?'):
                cleaned = message_lower.strip().rstrip('.,!?')
                if cleaned in direct_business_words or any(biz in cleaned for biz in direct_business_words):
                    extracted["business_type"] = cleaned
                    logger.info(f"✅ Found business type via single-word: {cleaned}")
        
        if extracted["business_type"]:
            logger.info(f"✅ Business type extracted: {extracted['business_type']}")
        else:
            logger.info(f"❌ No business type found in: '{current_message}'")
            
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
            
        # Look for budget patterns - exclude time patterns
        # Don't extract numbers if they're part of time (e.g., "10:00 AM")
        if not re.search(r'\d+:\d+\s*(?:am|pm|AM|PM)', current_message):
            # Only extract if: has $ sign, OR has budget keywords, OR is a large number (200+)
            budget_match = re.search(r'\$(\d+)\s*(?:al mes|mensuales|/mes|monthly|per month)?', current_message, re.IGNORECASE)
            if not budget_match:
                # Try without $ but with explicit budget keywords after number
                budget_match = re.search(r'(\d+)\s*(?:al mes|mensuales|/mes|monthly|per month|dólares|dolares|pesos)', current_message, re.IGNORECASE)
            if not budget_match:
                # Try with budget context words before number
                budget_match = re.search(r'(?:presupuesto|budget|inversion|inversión)\s*(?:es|de|:)?\s*(\d+)', current_message, re.IGNORECASE)
            if not budget_match:
                # Try large standalone numbers (200+) that might be budget
                budget_match = re.search(r'\b([2-9]\d{2,}|1[5-9]\d{2,})\b', current_message)
            
            if budget_match:
                extracted["budget"] = f"{budget_match.group(1)}/month"
        
        # Also check for budget confirmation responses
        if not extracted["budget"] and previous_score >= 5:  # Only check confirmations after initial qualification
            if validate_budget_confirmation(current_message, previous_score):
                extracted["budget"] = "300+/month"  # Confirmed minimum budget
                logger.info("Detected budget confirmation")
        
        # Check for email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, current_message)
        if email_match:
            extracted["email"] = email_match.group(0)
            logger.info(f"Found email: {extracted['email']}")
        
        # Final values for GHL update (calculate first)
        final_name = extracted["name"] or previous_name
        final_business = extracted["business_type"] or previous_business
        final_budget = extracted["budget"] or previous_budget
        final_email = extracted.get("email") or existing_extracted.get("email", "")
        
        # Check for problems/goals
        has_problem = False
        problem_keywords = [
            "perdiendo", "perder", "pierdo", "no puedo", "necesito", "quiero",
            "busco", "ayuda", "problema", "dificultad", "automatizar", "mejorar"
        ]
        for keyword in problem_keywords:
            if keyword in message_lower:
                has_problem = True
                extracted["goal"] = keyword
                logger.info(f"Found problem/goal: {keyword}")
                break
        
        final_goal = extracted.get("goal", "")
        
        # Calculate score based on what we have overall (not just new info)
        score = 1  # Base score for any message
        
        # Consider all information (previous + new)
        if final_name:
            score += 1
            
        if final_business and final_business != "NO_MENCIONADO":
            score += 2
            
        if has_problem:
            score += 2  # Problem/goal adds significant value
            
        if final_budget:
            score += 2
            # Check for high budget - be more flexible with the check
            budget_str = str(final_budget).lower()
            if any(amt in budget_str for amt in ["300", "500", "800", "1000"]):
                score += 1  # High budget
                logger.info(f"High budget detected: {final_budget}")
                
        # Email adds another point for hot lead qualification
        if final_email:
            score += 1
            logger.info(f"Email provided: {final_email}")
        
        # Use calculated score or previous score, whichever is higher
        final_score = max(score, previous_score)
        
        logger.info(f"Lead analysis: Score {previous_score} -> {final_score}")
        logger.info(f"Extracted - Name: {extracted['name']}, Business: {extracted['business_type']}, Budget: {extracted['budget']}")
        logger.info(f"Final values - Name: {final_name}, Business: {final_business}, Budget: {final_budget}")
        
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
                "budget": final_budget,
                "email": final_email,
                "score": final_score  # Add score to extracted data for persistence
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