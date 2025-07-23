"""
Smart Router - Combines intelligence analysis and routing in one efficient node
Tracks scores, reasons, and updates GHL with notes at each step
"""
from typing import Dict, Any, List, Tuple
from langchain_core.messages import BaseMessage
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
# GHL client will be initialized when needed
from app.state.message_manager import MessageManager
from app.utils.langsmith_debug import debug_node, log_to_langsmith, debugger
import json

logger = get_logger("smart_router")


class SmartRouter:
    """Combined intelligence analyzer and router with tracking"""
    
    def __init__(self):
        self.model = create_openai_model(temperature=0.0)
    
    async def analyze_and_route(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the conversation and route to appropriate agent.
        Updates GHL with notes about score changes and routing decisions.
        """
        try:
            messages = state.get("messages", [])
            contact_id = state.get("contact_id")
            previous_score = state.get("lead_score", 0)
            previous_agent = state.get("current_agent", "none")
            
            # Log routing context to LangSmith
            log_to_langsmith({
                "contact_id": contact_id,
                "previous_score": previous_score,
                "previous_agent": previous_agent,
                "message_count": len(messages),
                "has_extracted_data": bool(state.get("extracted_data")),
            }, "routing_context")
            
            # Get current message
            current_message = self._get_last_customer_message(messages)
            if not current_message:
                logger.info("No new customer message to route (may already be processed)")
                log_to_langsmith({
                    "issue": "no_customer_message",
                    "fallback_agent": "maria",
                    "reason": "No new message to analyze"
                }, "routing_fallback")
                return self._create_routing_response("maria", 0, "No new message to analyze", state)
            
            # Analyze the message for lead scoring and data extraction
            analysis = await self._analyze_message(current_message, messages, state)
            
            # Log analysis results to LangSmith
            log_to_langsmith({
                "current_message": current_message[:200],
                "lead_score": analysis["lead_score"],
                "score_reason": analysis["score_reason"],
                "intent": analysis["intent"],
                "urgency": analysis["urgency"],
                "sentiment": analysis["sentiment"],
                "extracted_data": analysis["extracted_data"],
            }, "message_analysis")
            
            # Determine routing based on score
            new_score = analysis["lead_score"]
            routing_decision = self._determine_routing(new_score, analysis)
            
            # Log routing decision to LangSmith
            debugger.log_routing_decision(
                previous_agent,
                routing_decision["next_agent"],
                routing_decision["routing_reason"],
                new_score
            )
            
            # Track score changes
            score_change_note = self._track_score_change(
                previous_score, 
                new_score, 
                analysis["score_reason"]
            )
            
            # Track routing changes
            routing_change_note = self._track_routing_change(
                previous_agent,
                routing_decision["next_agent"],
                routing_decision["routing_reason"]
            )
            
            # Update GHL with notes if there are changes
            if contact_id and (score_change_note or routing_change_note):
                await self._update_ghl_notes(
                    contact_id,
                    score_change_note,
                    routing_change_note,
                    analysis
                )
            
            # Create comprehensive response
            return {
                # Routing info
                "next_agent": routing_decision["next_agent"],
                "agent_task": routing_decision["agent_task"],
                "routing_reason": routing_decision["routing_reason"],
                
                # Score tracking
                "lead_score": new_score,
                "previous_score": previous_score,
                "score_reason": analysis["score_reason"],
                "score_changed": previous_score != new_score,
                
                # Extracted data
                "extracted_data": analysis["extracted_data"],
                
                # Analysis metadata
                "intent": analysis["intent"],
                "urgency": analysis["urgency"],
                "sentiment": analysis["sentiment"],
                
                # Tracking
                "score_history": state.get("score_history", []) + [{
                    "score": new_score,
                    "reason": analysis["score_reason"],
                    "timestamp": analysis["timestamp"]
                }],
                
                # Flags
                "router_complete": True,
                "needs_escalation": new_score >= 8
            }
            
        except Exception as e:
            logger.error(f"Smart router error: {str(e)}", exc_info=True)
            return self._create_routing_response("maria", 0, f"Router error: {str(e)}", state)
    
    async def _analyze_message(
        self, 
        current_message: str, 
        messages: List[BaseMessage],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to analyze the message for scoring and data extraction"""
        
        # Get existing data
        existing_data = state.get("extracted_data", {})
        
        # Get business context
        from app.config import get_settings
        settings = get_settings()
        
        # Adapt analysis context based on customer needs
        if settings.adapt_to_customer:
            analysis_context = "customer conversation"
        else:
            analysis_context = f"{settings.service_type} conversation"
        
        prompt = f"""Analyze this {analysis_context} for lead qualification.

Current message: {current_message}

Existing data collected:
{json.dumps(existing_data, indent=2)}

Analyze and provide:
1. Lead score (0-10) based on:
   - Interest level (questions about service, pricing, demo)
   - Business information provided
   - Urgency indicators
   - Budget discussions
   - Problem clarity and fit with our solutions
   
2. Extract any new information:
   - Name
   - Business type
   - Contact details (phone, email)
   - Budget range
   - Specific needs/problems (IMPORTANT: Extract their ACTUAL problem)
   - Timeline/urgency

3. Detect intent:
   - greeting
   - question
   - information_provided
   - appointment_interest
   - objection
   - confirmation
   - problem_statement

4. Assess urgency (low/medium/high)

5. Sentiment (positive/neutral/negative)

6. Problem match: Does their problem align with {settings.service_type}? (yes/no/maybe)

Provide response as JSON:
{{
    "lead_score": 0-10,
    "score_reason": "Brief explanation",
    "extracted_data": {{
        "name": "if found",
        "business_type": "if found",
        "email": "if found",
        "phone": "if found",
        "budget": "if found",
        "goal": "if found (ACTUAL customer problem)",
        "timeline": "if found"
    }},
    "intent": "detected intent",
    "urgency": "low/medium/high",
    "sentiment": "positive/neutral/negative",
    "problem_match": "yes/no/maybe"
}}"""

        response = await self.model.ainvoke(prompt)
        
        try:
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {str(e)}")
            # Fallback analysis
            analysis = {
                "lead_score": 1,
                "score_reason": "Could not parse analysis",
                "extracted_data": existing_data,
                "intent": "unknown",
                "urgency": "low",
                "sentiment": "neutral"
            }
        
        # Merge with existing data
        merged_data = {**existing_data}
        for key, value in analysis.get("extracted_data", {}).items():
            if value and value != "if found" and value != "NOT PROVIDED":
                merged_data[key] = value
        
        # Context-specific data enrichment
        problem_match = analysis.get("problem_match", "maybe")
        if settings.adapt_to_customer:
            # If customer mentioned restaurant/food, update business type
            if "restaurant" in merged_data.get("business_type", "").lower():
                if not merged_data.get("goal"):
                    merged_data["goal"] = "customer retention and engagement"
                merged_data["industry"] = "food_service"
            
            # If they mention being busy with messages
            elif any(word in current_message.lower() for word in ['mensaje', 'whatsapp', 'ocupado']):
                if not merged_data.get("goal"):
                    merged_data["goal"] = "automate message responses"
                merged_data["industry"] = "general_business"
                
            # Adjust score based on problem match
            if problem_match == "no" and analysis["lead_score"] > 3:
                # Lower score if problem doesn't match our services
                analysis["lead_score"] = max(3, analysis["lead_score"] - 2)
                analysis["score_reason"] += " (Adjusted down - problem mismatch)"
        
        analysis["extracted_data"] = merged_data
        analysis["timestamp"] = self._get_timestamp()
        
        return analysis
    
    def _determine_routing(self, score: int, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine which agent should handle based on score and context"""
        
        # Check for appointment readiness
        has_email = bool(analysis["extracted_data"].get("email"))
        shows_high_interest = analysis["intent"] == "appointment_interest"
        
        if score >= 8 or (score >= 7 and has_email and shows_high_interest):
            return {
                "next_agent": "sofia",
                "agent_task": "Cliente calificado para agendar demo",
                "routing_reason": f"Alta puntuación ({score}/10) + {('email disponible' if has_email else 'alto interés')}"
            }
        elif score >= 5:
            return {
                "next_agent": "carlos",
                "agent_task": "Calificar lead y mostrar valor",
                "routing_reason": f"Puntuación media ({score}/10) - necesita calificación"
            }
        else:
            return {
                "next_agent": "maria",
                "agent_task": "Atender y recopilar información inicial",
                "routing_reason": f"Puntuación inicial ({score}/10) - fase de descubrimiento"
            }
    
    def _track_score_change(self, old_score: int, new_score: int, reason: str) -> str:
        """Create note about score change"""
        if old_score == new_score:
            return ""
        
        direction = "📈" if new_score > old_score else "📉"
        return f"{direction} Score: {old_score} → {new_score} | Razón: {reason}"
    
    def _track_routing_change(self, old_agent: str, new_agent: str, reason: str) -> str:
        """Create note about routing change"""
        if old_agent == new_agent or old_agent == "none":
            return ""
        
        return f"🔄 Ruta: {old_agent} → {new_agent} | {reason}"
    
    async def _update_ghl_notes(
        self, 
        contact_id: str,
        score_note: str,
        routing_note: str,
        analysis: Dict[str, Any]
    ):
        """Update GHL contact with tracking notes"""
        try:
            notes = []
            
            if score_note:
                notes.append(score_note)
            
            if routing_note:
                notes.append(routing_note)
            
            # Add extracted data updates
            new_data = []
            for key, value in analysis["extracted_data"].items():
                if value and value != "NOT PROVIDED":
                    new_data.append(f"{key}: {value}")
            
            if new_data:
                notes.append(f"📋 Datos: {', '.join(new_data)}")
            
            # For now, just log the updates (GHL client needs proper initialization)
            if notes:
                note_text = f"[{self._get_timestamp()}] " + " | ".join(notes)
                logger.info(f"Would update GHL contact {contact_id}: {note_text}")
            
            logger.info(f"Analysis complete for {contact_id}: Score={analysis['lead_score']}, Intent={analysis['intent']}")
            
        except Exception as e:
            logger.error(f"Failed to update GHL notes: {str(e)}")
    
    def _get_last_customer_message(self, messages: List[BaseMessage]) -> str:
        """Extract the last customer message"""
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
                if not hasattr(msg, 'name') or not msg.name:
                    return msg.content
        return ""
    
    def _create_routing_response(
        self, 
        agent: str, 
        score: int, 
        reason: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a routing response with defaults"""
        return {
            "next_agent": agent,
            "agent_task": "Atender al cliente",
            "routing_reason": reason,
            "lead_score": score,
            "router_complete": True,
            "score_history": state.get("score_history", [])
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Create singleton instance
smart_router = SmartRouter()


@debug_node("smart_router")
async def smart_router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Smart router node for workflow"""
    return await smart_router.analyze_and_route(state)


# Export
__all__ = ["smart_router_node", "SmartRouter"]