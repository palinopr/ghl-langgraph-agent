"""
Supervisor Brain with AI Analyzer Fallback
Uses pattern extraction first, then AI analysis for complex cases
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
from app.agents.ai_analyzer import analyze_customer_intent, calculate_smart_score
import re

logger = get_logger("supervisor_brain_ai")

# Log deployment info once at module load
log_deployment_info()


def extract_and_update_lead(
    current_message: str,
    contact_info: Dict[str, Any],
    previous_fields: Dict[str, Any],
    existing_extracted: Dict[str, Any],
    previous_score: int
) -> Dict[str, Any]:
    """
    Enhanced extraction with AI fallback
    Returns extracted data and new score
    """
    
    # STEP 1: Try pattern extraction first (fast)
    extracted = {"name": None, "business_type": None, "budget": None}
    
    # Enhanced business extraction
    logger.info(f"🔍 Attempting to extract business from: '{current_message}'")
    
    # Direct business type matches (including plurals)
    business_patterns = {
        "restaurante": ["restaurante", "restaurantes", "restaurant", "restaurants"],
        "tienda": ["tienda", "tiendas"],
        "salon": ["salon", "salón", "salones"],
        "barberia": ["barbería", "barberia", "barberías", "barberias"],
        "clinica": ["clinica", "clínica", "clinicas", "clínicas"],
        "consultorio": ["consultorio", "consultorios"],
        "agencia": ["agencia", "agencias"],
        "hotel": ["hotel", "hoteles"],
        "gym": ["gym", "gimnasio", "gyms", "gimnasios"],
        "spa": ["spa", "spas"],
        "cafe": ["café", "cafe", "cafés", "cafes"],
        "pizzeria": ["pizzería", "pizzeria", "pizzerías", "pizzerias"],
        "panaderia": ["panadería", "panaderia", "panaderías", "panaderias"],
        "farmacia": ["farmacia", "farmacias"],
        "negocio": ["negocio", "negocios"]
    }
    
    message_lower = current_message.lower().strip()
    
    # Check all variations
    found_business = None
    for base, variations in business_patterns.items():
        for variant in variations:
            if variant in message_lower:
                extracted["business_type"] = base
                found_business = base
                logger.info(f"✅ Found business type via pattern: {base}")
                break
        if found_business:
            break
    
    # Name extraction patterns
    name_patterns = [
        r"(?:me llamo|mi nombre es|soy)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+)",
        r"^([A-ZÁÉÍÓÚÑa-záéíóúñ]+)$"  # Single word that could be a name
    ]
    
    # Common business words that should NOT be treated as names
    business_words = set()
    for variations in business_patterns.values():
        business_words.update(variations)
    
    for pattern in name_patterns:
        match = re.search(pattern, current_message, re.IGNORECASE)
        if match:
            potential_name = match.group(1).strip().title()
            # Don't extract business words as names
            if (len(potential_name) > 2 and 
                potential_name.lower() not in ['hola', 'buenas', 'gracias'] and
                potential_name.lower() not in business_words):
                extracted["name"] = potential_name
                logger.info(f"Found name: {potential_name}")
                break
    
    # Budget extraction
    if not re.search(r'\d+:\d+\s*(?:am|pm|AM|PM)', current_message):
        budget_patterns = [
            r'\$?\s*(\d{3,})\s*(?:/mes|mensuales?|al mes)?',
            r'(?:como unos?|aproximadamente|más o menos|alrededor de)\s*\$?\s*(\d{3,})',
            r'(?:presupuesto|inversión|gastar?)\s*(?:de|es)?\s*\$?\s*(\d{3,})'
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, current_message, re.IGNORECASE)
            if match:
                amount = match.group(1)
                if int(amount) >= 100:
                    extracted["budget"] = f"{amount}/month"
                    logger.info(f"Found budget: {amount}/month")
                    break
    
    # Calculate pattern-based score
    pattern_score = calculate_pattern_score(
        extracted, previous_fields, existing_extracted, 
        current_message, previous_score
    )
    
    # STEP 2: Decide if we need AI analysis
    needs_ai_analysis = should_use_ai_analysis(
        extracted, current_message, pattern_score
    )
    
    if needs_ai_analysis:
        logger.info("🤖 Pattern extraction incomplete, using AI analyzer...")
        return {
            "extracted": extracted,
            "score": pattern_score,
            "needs_ai": True
        }
    
    # Return pattern results if sufficient
    return {
        "extracted": extracted,
        "score": pattern_score,
        "needs_ai": False
    }


def should_use_ai_analysis(extracted: Dict, message: str, score: int) -> bool:
    """
    Decide if we need AI analysis
    """
    message_lower = message.lower()
    
    # Indicators that suggest business context but wasn't extracted
    business_indicators = [
        "perdiendo", "perder", "cerrando", "problema", 
        "ayuda", "cliente", "reserva", "venta", "negocio",
        "no puedo", "necesito", "urgente"
    ]
    
    has_business_indicator = any(word in message_lower for word in business_indicators)
    
    # Use AI if:
    # 1. Message suggests business but we didn't extract it
    if has_business_indicator and not extracted.get("business_type"):
        return True
    
    # 2. Low score but complex message
    if score <= 2 and len(message.split()) > 5:
        return True
    
    # 3. Message contains questions or multiple sentences
    if "?" in message or message.count(".") > 1:
        return True
    
    return False


def calculate_pattern_score(
    extracted: Dict, 
    previous_fields: Dict, 
    existing_extracted: Dict,
    current_message: str,
    previous_score: int
) -> int:
    """Calculate score based on pattern extraction"""
    
    # Merge all data
    final_name = extracted.get("name") or existing_extracted.get("name") or previous_fields.get("name")
    final_business = extracted.get("business_type") or existing_extracted.get("business_type") or previous_fields.get("business_type")
    final_budget = extracted.get("budget") or existing_extracted.get("budget") or previous_fields.get("budget")
    
    # Check for problems/urgency
    message_lower = current_message.lower()
    problem_keywords = [
        "perdiendo", "perder", "pierdo", "no puedo", "necesito", "quiero",
        "busco", "ayuda", "problema", "dificultad", "automatizar", "mejorar",
        "urgente", "cerrando", "cayendo"
    ]
    has_problem = any(keyword in message_lower for keyword in problem_keywords)
    
    # Calculate score
    score = 1  # Base
    
    if final_name:
        score += 1
        
    if final_business and final_business != "NO_MENCIONADO":
        score += 2
        
    if has_problem:
        score += 2
        
    # Business owner with problem needs budget for high score
    if final_business and final_business != "NO_MENCIONADO" and has_problem:
        score = max(score, 4)  # NOT 6! Need budget confirmation first
        
    if final_budget:
        score += 2
        # High budget check
        budget_str = str(final_budget).lower()
        if any(amt in budget_str for amt in ["300", "500", "800", "1000"]):
            score += 1
    
    # Never decrease score
    return max(score, previous_score)


@debug_async("SUPERVISOR_BRAIN_AI")
async def supervisor_brain_ai_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced supervisor with AI fallback
    """
    contact_id = state.get("contact_id")
    logger.info(f"AI Supervisor analyzing lead {contact_id}")
    
    try:
        # Get current message
        current_message = ""
        webhook_data = state.get("webhook_data", {})
        if webhook_data and webhook_data.get("message"):
            current_message = webhook_data["message"]
        else:
            # Get from messages
            messages = state.get("messages", [])
            for msg in messages:
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                    additional_kwargs = getattr(msg, 'additional_kwargs', {})
                    if additional_kwargs.get('source') != 'ghl_history':
                        current_message = msg.content
                        break
        
        logger.info(f"Analyzing message: {current_message}")
        
        # Get context
        contact_info = state.get("contact_info", {})
        previous_fields = state.get("previous_custom_fields", {})
        existing_extracted = state.get("extracted_data", {})
        
        
        # CRITICAL: Extract data from historical messages to fix context blindness
        messages = state.get("messages", [])
        historical_business = None
        historical_problem = False
        
        for msg in messages:
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get('source') == 'ghl_history':
                    hist_content = msg.content.lower()
                    
                    # Check for business mentions in history
                    if "restaurante" in hist_content or "restaurant" in hist_content:
                        historical_business = "restaurante"
                    
                    # Also check for problems (separate check, not elif!)
                    if "perdiendo" in hist_content or "reservas" in hist_content or "no puedo contestar" in hist_content:
                        historical_problem = True
                        
        if historical_business and (not existing_extracted.get("business_type") or existing_extracted["business_type"] == "NO_MENCIONADO"):
            existing_extracted["business_type"] = historical_business
            logger.info(f"Found business in conversation history: {historical_business}")
            
        # Get previous score first
        try:
            score_from_extracted = int(existing_extracted.get("score", 0))
            score_from_fields = int(previous_fields.get("score", "0") or "0")
            score_from_state = int(state.get("lead_score", 0))
            previous_score = max(score_from_extracted, score_from_fields, score_from_state)
        except:
            previous_score = 0
            
        # Boost score if we found historical context AND current message is business-related
        current_msg_lower = current_message.lower()
        is_business_related = any(indicator in current_msg_lower for indicator in [
            "negocio", "restaurante", "ayuda", "necesito", "problema", 
            "reserva", "cliente", "perdiendo", "automatizar", "sistema",
            "cita", "agendar", "horario", "disponible", "consulta"
        ])
        
        if historical_business and historical_problem and is_business_related:
            # Modest boost for returning customers discussing business
            previous_score = min(previous_score + 2, 6)
            logger.info(f"Business context detected in current message - boost applied (score: {previous_score})")
        elif historical_business and historical_problem:
            # Small recognition boost for returning customers
            previous_score = min(previous_score + 1, previous_score + 1)
            logger.info("Returning customer recognized - small boost applied")
        
        # STEP 1: Try pattern extraction
        pattern_result = extract_and_update_lead(
            current_message, contact_info, previous_fields, 
            existing_extracted, previous_score
        )
        
        # STEP 2: Use AI if needed
        if pattern_result["needs_ai"]:
            # Prepare conversation history
            messages = state.get("messages", [])
            conversation_history = []
            for msg in messages[-10:]:  # Last 10 messages
                if hasattr(msg, 'type') and hasattr(msg, 'content'):
                    conversation_history.append({
                        "type": msg.type,
                        "content": msg.content
                    })
            
            # Prepare context
            previous_context = {
                "name": previous_fields.get("name") or existing_extracted.get("name"),
                "business_type": previous_fields.get("business_type") or existing_extracted.get("business_type"),
                "budget": previous_fields.get("budget") or existing_extracted.get("budget"),
                "score": str(previous_score)
            }
            
            # Get AI analysis
            ai_result = await analyze_customer_intent(
                current_message,
                conversation_history,
                previous_context
            )
            
            logger.info(f"AI Analysis complete: {ai_result}")
            
            # Merge results
            final_extracted = pattern_result["extracted"].copy()
            
            # Update with AI findings
            if ai_result.get("business_type"):
                # Normalize business type
                ai_business = ai_result["business_type"].lower()
                if "restaurant" in ai_business or "restaurante" in ai_business:
                    final_extracted["business_type"] = "restaurante"
                elif ai_business and ai_business not in ["None", "null"]:
                    final_extracted["business_type"] = ai_business
            
            # Get key info from AI
            key_info = ai_result.get("key_info") or {}
            if isinstance(key_info, dict):
                if key_info.get("name"):
                    final_extracted["name"] = key_info["name"]
                if key_info.get("budget"):
                    final_extracted["budget"] = key_info["budget"]
                if key_info.get("email"):
                    final_extracted["email"] = key_info["email"]
            
            # Calculate AI-based score
            final_score = calculate_smart_score(ai_result, previous_score)
            
            # Store AI insights for agents
            state["ai_insights"] = {
                "intent": ai_result.get("intent"),
                "urgency": ai_result.get("urgency"),
                "sentiment": ai_result.get("sentiment"),
                "recommended_action": ai_result.get("recommended_action")
            }
        else:
            # Use pattern results
            final_extracted = pattern_result["extracted"]
            final_score = pattern_result["score"]
            state["ai_insights"] = None
        
        # Merge with previous data
        final_name = final_extracted.get("name") or existing_extracted.get("name") or previous_fields.get("name")
        final_business = final_extracted.get("business_type") or existing_extracted.get("business_type") or previous_fields.get("business_type", "NO_MENCIONADO")
        final_budget = final_extracted.get("budget") or existing_extracted.get("budget") or previous_fields.get("budget")
        final_email = final_extracted.get("email") or existing_extracted.get("email") or previous_fields.get("email")
        
        # Log final results
        logger.info(f"Final extraction: name={final_name}, business={final_business}, budget={final_budget}, score={final_score}")
        
        # STEP 3: Update GHL
        ghl_client = GHLClient()
        
        # Prepare updates
        updates = {
            FIELD_MAPPINGS["score"]: str(final_score),
            FIELD_MAPPINGS["name"]: final_name or "",
            FIELD_MAPPINGS["business_type"]: final_business,
            FIELD_MAPPINGS["budget"]: final_budget or ""
        }
        
        if final_email:
            updates[FIELD_MAPPINGS.get("email", "email")] = final_email
        
        # Add tags
        tags = []
        if final_score >= 8:
            tags.extend(["hot-lead", "ready-to-buy"])
        elif final_score >= 5:
            tags.extend(["warm-lead", "needs-qualification"])
        else:
            tags.extend(["cold-lead", "needs-nurturing"])
        
        # Update GHL
        try:
            # Update custom fields
            for field_id, value in updates.items():
                await ghl_client.update_contact_field(contact_id, field_id, value)
            
            # Add tags
            if tags:
                result = await ghl_client.update_contact(contact_id, {"tags": tags})
            logger.info(f"GHL updated successfully")
            
            # Track changes for note
            changes = []
            if final_name and final_name != previous_fields.get("name"):
                changes.append(f"Name: {previous_fields.get('name', 'None')} → {final_name}")
            if final_business != previous_fields.get("business_type", "NO_MENCIONADO"):
                changes.append(f"Business: {previous_fields.get('business_type', 'None')} → {final_business}")
            if final_budget and final_budget != previous_fields.get("budget"):
                changes.append(f"Budget: {previous_fields.get('budget', 'None')} → {final_budget}")
            if final_score != previous_score:
                changes.append(f"Score: {previous_score} → {final_score}")
            
            # Determine analysis method
            analysis_method = "AI-enhanced analysis" if pattern_result["needs_ai"] else "Pattern-based extraction"
            
            # Create analysis note
            note_content = f"""Lead Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}
Score: {final_score}/10 (Previous: {previous_score})

EXTRACTED DATA:
- Name: {final_name or 'Not provided'}
- Business: {final_business}
- Budget: {final_budget or 'Not confirmed'}
- Email: {final_email or contact_info.get('email', 'Not provided')}

CHANGES DETECTED:
{', '.join(changes) if changes else 'No changes detected'}

ANALYSIS METHOD:
{analysis_method}

LEAD CATEGORY:
{'HOT LEAD (8-10)' if final_score >= 8 else 'WARM LEAD (5-7)' if final_score >= 5 else 'COLD LEAD (1-4)'}

TAGS APPLIED:
{', '.join(tags) if tags else 'No tags applied'}
"""
            
            try:
                await ghl_client.create_note(contact_id, note_content)
                logger.info("✅ Created analysis note in GHL")
            except Exception as e:
                logger.error(f"Failed to create note: {e}")
                
        except Exception as e:
            logger.error(f"Failed to update GHL: {str(e)}")
        
        # STEP 4: Determine routing
        # Check for AI recommendation first
        ai_insights = state.get("ai_insights")
        if ai_insights and ai_insights.get("recommended_action"):
            action = ai_insights["recommended_action"]
            if action == "OFFER_APPOINTMENT":
                next_agent = "sofia"
            elif action in ["QUALIFY_BUSINESS", "ADDRESS_CONCERN"]:
                next_agent = "carlos"
            else:
                # Fall back to score-based routing
                if final_score >= 8:
                    next_agent = "sofia"
                elif final_score >= 5:
                    next_agent = "carlos"
                else:
                    next_agent = "maria"
        else:
            # Score-based routing
            if final_score >= 8:
                next_agent = "sofia"
            elif final_score >= 5:
                next_agent = "carlos"
            else:
                next_agent = "maria"
        
        logger.info(f"Routing to {next_agent} (score: {final_score})")
        
        # Return updated state
        return {
            "supervisor_complete": True,
            "lead_score": final_score,
            "next_agent": next_agent,
            "extracted_data": {
                "name": final_name,
                "business_type": final_business,
                "budget": final_budget,
                "email": final_email,
                "score": final_score
            },
            # Don't add debug messages - they're visible to customers!
            "messages": state["messages"]
        }
        
    except Exception as e:
        logger.error(f"Supervisor error: {str(e)}", exc_info=True)
        # Default routing on error
        return {
            "supervisor_complete": True,
            "lead_score": state.get("lead_score", 1),
            "next_agent": "maria",
            "error": str(e)
        }