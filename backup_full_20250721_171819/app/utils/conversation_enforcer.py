"""
Conversation Flow Enforcer - Ensures agents follow EXACT conversation rules
This is the STRICT state machine that prevents agents from deviating
"""
from typing import Dict, Any, List, Optional, Literal, Tuple
from enum import Enum
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import re
from app.utils.simple_logger import get_logger
from app.utils.conversation_analyzer import ConversationAnalyzer
from app.state.enhanced_conversation_state import ConversationStage as EnhancedStage

logger = get_logger("conversation_enforcer")


class ConversationStage(Enum):
    """Exact conversation stages - NO OTHER STAGES ALLOWED"""
    # Initial stages
    GREETING = "greeting"
    WAITING_FOR_NAME = "waiting_for_name"
    WAITING_FOR_BUSINESS = "waiting_for_business"
    WAITING_FOR_PROBLEM = "waiting_for_problem"
    WAITING_FOR_BUDGET = "waiting_for_budget"
    WAITING_FOR_EMAIL = "waiting_for_email"
    # Appointment stages
    OFFERING_TIMES = "offering_times"
    WAITING_FOR_TIME_SELECTION = "waiting_for_time_selection"
    CONFIRMING_APPOINTMENT = "confirming_appointment"
    # End stages
    COMPLETED = "completed"
    ESCALATING = "escalating"


class ConversationEnforcer:
    """
    Enforces STRICT conversation flow rules
    This is the source of truth for what agents can say and when
    """
    
    # EXACT templates for each stage - NO VARIATIONS ALLOWED
    STAGE_TEMPLATES = {
        ConversationStage.GREETING: {
            "es": "¡Hola! Soy de Main Outlet Media. Ayudamos a negocios como el tuyo a automatizar WhatsApp para nunca perder clientes. ¿Cuál es tu nombre?",
            "en": "Hi! I'm from Main Outlet Media. We help businesses like yours automate WhatsApp to never miss a customer. What's your name?"
        },
        ConversationStage.WAITING_FOR_NAME: {
            "es": "Mucho gusto, {name}. ¿Qué tipo de negocio tienes?",
            "en": "Nice to meet you, {name}. What type of business do you have?"
        },
        ConversationStage.WAITING_FOR_BUSINESS: {
            "es": "Ya veo, {business}. ¿Cuál es tu mayor desafío con los mensajes de WhatsApp?",
            "en": "I see, {business}. What's your biggest challenge with WhatsApp messages?"
        },
        ConversationStage.WAITING_FOR_PROBLEM: {
            "es": "Definitivamente puedo ayudarte con eso. Mis soluciones empiezan en $300/mes. ¿Te funciona ese presupuesto?",
            "en": "I can definitely help with that. My solutions start at $300/month. Does that budget work for you?"
        },
        ConversationStage.WAITING_FOR_BUDGET: {
            "es": "¡Perfecto! Para coordinar nuestra videollamada, ¿cuál es tu correo electrónico?",
            "en": "Perfect! To coordinate our video call, what's your email?"
        },
        ConversationStage.WAITING_FOR_EMAIL: {
            "es": "¡Excelente! Te enviaré el enlace de Google Meet a {email}. ¿Qué día y hora te funciona mejor?",
            "en": "Excellent! I'll send the Google Meet link to {email}. What day and time works best for you?"
        },
        ConversationStage.OFFERING_TIMES: {
            "es": "¡Excelente! Tengo estos horarios disponibles:\n\n📅 Mañana:\n• 10:00 AM\n• 2:00 PM\n• 4:00 PM\n\n¿Cuál prefieres?",
            "en": "Excellent! I have these times available:\n\n📅 Tomorrow:\n• 10:00 AM\n• 2:00 PM\n• 4:00 PM\n\nWhich do you prefer?"
        },
        ConversationStage.WAITING_FOR_TIME_SELECTION: {
            "es": "USE_APPOINTMENT_TOOL",  # Special marker to use tool instead of template
            "en": "USE_APPOINTMENT_TOOL"
        },
        ConversationStage.CONFIRMING_APPOINTMENT: {
            "es": "¡CONFIRMADO! Te veo el {date} a las {time}. Te enviaré el enlace de Google Meet a {email} con todos los detalles. ¡Nos vemos pronto!",
            "en": "CONFIRMED! I'll see you on {date} at {time}. I'll send the Google Meet link to {email} with all the details. See you soon!"
        }
    }
    
    # Rules for transitioning between stages
    STAGE_TRANSITIONS = {
        ConversationStage.GREETING: ConversationStage.WAITING_FOR_NAME,
        ConversationStage.WAITING_FOR_NAME: ConversationStage.WAITING_FOR_BUSINESS,
        ConversationStage.WAITING_FOR_BUSINESS: ConversationStage.WAITING_FOR_PROBLEM,
        ConversationStage.WAITING_FOR_PROBLEM: ConversationStage.WAITING_FOR_BUDGET,
        ConversationStage.WAITING_FOR_BUDGET: ConversationStage.WAITING_FOR_EMAIL,
        ConversationStage.WAITING_FOR_EMAIL: ConversationStage.OFFERING_TIMES,
        ConversationStage.OFFERING_TIMES: ConversationStage.WAITING_FOR_TIME_SELECTION,
        ConversationStage.WAITING_FOR_TIME_SELECTION: ConversationStage.CONFIRMING_APPOINTMENT,
        ConversationStage.CONFIRMING_APPOINTMENT: ConversationStage.COMPLETED,
    }
    
    def __init__(self):
        self.logger = logger
    
    def analyze_conversation(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        Analyze conversation to determine EXACT current state
        Now uses the enhanced ConversationAnalyzer to prevent repetition
        """
        # Use the enhanced analyzer that properly tracks what's been asked/answered
        enhanced_analysis = ConversationAnalyzer.analyze_conversation(messages)
        
        # Convert to our format while keeping all the enhanced tracking
        analysis = {
            "current_stage": self._map_enhanced_stage(enhanced_analysis["current_stage"]),
            "collected_data": {
                "name": enhanced_analysis["collected_data"]["name"],
                "business": enhanced_analysis["collected_data"]["business_type"],
                "problem": enhanced_analysis["collected_data"]["challenge"],
                "budget_confirmed": enhanced_analysis["collected_data"]["budget_confirmed"],
                "email": enhanced_analysis["collected_data"]["email"]
            },
            "language": enhanced_analysis["language"],
            "last_question_asked": enhanced_analysis.get("last_ai_question"),
            "expecting_answer_for": enhanced_analysis["expecting_answer_for"],
            "next_action": self._determine_next_action(enhanced_analysis),
            "allowed_response": None,
            "forbidden_actions": [],
            # Keep enhanced tracking info
            "questions_asked": list(enhanced_analysis["questions_asked"]),
            "next_question_to_ask": enhanced_analysis["next_question_to_ask"]
        }
        
        # Check for appointment time selection
        selected_time = False
        current_msg_is_time_selection = False
        
        # Check if appointment times were offered
        offered_times = False
        for msg in messages:
            if isinstance(msg, AIMessage) or (hasattr(msg, 'role') and msg.role == "assistant"):
                content = msg.content.lower() if hasattr(msg, 'content') else ""
                if ("horarios disponibles" in content or 
                    "10:00 am" in content or 
                    "tengo estos horarios" in content or
                    "¿cuál prefieres?" in content):
                    offered_times = True
                    break
        
        # Check last message for time selection
        if messages and len(messages) > 0:
            last_human_msg = messages[-1]
            if isinstance(last_human_msg, HumanMessage) or (hasattr(last_human_msg, 'type') and last_human_msg.type == "human"):
                content = last_human_msg.content.lower() if hasattr(last_human_msg, 'content') else ""
                time_indicators = ["am", "pm", ":00", "primera", "segunda", "tercera", 
                                 "10:", "2:", "4:", "mañana", "tarde"]
                if any(indicator in content for indicator in time_indicators):
                    selected_time = True
                    current_msg_is_time_selection = True
        
        # Override stage for appointment flow
        if offered_times and current_msg_is_time_selection:
            analysis["current_stage"] = ConversationStage.WAITING_FOR_TIME_SELECTION
            analysis["next_action"] = "PROCESS_TIME_SELECTION"
        elif offered_times and selected_time and not current_msg_is_time_selection:
            analysis["current_stage"] = ConversationStage.CONFIRMING_APPOINTMENT
            analysis["next_action"] = "CONFIRM_APPOINTMENT"
        
        # Set allowed response based on stage
        self._set_allowed_response(analysis)
        
        # Set forbidden actions
        analysis["forbidden_actions"] = self._get_forbidden_actions(analysis)
        
        # Log what we're tracking to prevent repetition
        if analysis["questions_asked"]:
            logger.info(f"Questions already asked: {', '.join(analysis['questions_asked'])}")
        if analysis["expecting_answer_for"]:
            logger.info(f"Expecting answer for: {analysis['expecting_answer_for']}")
        
        return analysis
    
    def _map_enhanced_stage(self, enhanced_stage: EnhancedStage) -> ConversationStage:
        """Map enhanced stages to our conversation stages"""
        mapping = {
            EnhancedStage.GREETING: ConversationStage.GREETING,
            EnhancedStage.COLLECTING_NAME: ConversationStage.WAITING_FOR_NAME,
            EnhancedStage.COLLECTING_BUSINESS: ConversationStage.WAITING_FOR_BUSINESS,
            EnhancedStage.COLLECTING_CHALLENGE: ConversationStage.WAITING_FOR_PROBLEM,
            EnhancedStage.COLLECTING_BUDGET: ConversationStage.WAITING_FOR_BUDGET,
            EnhancedStage.COLLECTING_EMAIL: ConversationStage.WAITING_FOR_EMAIL,
            EnhancedStage.OFFERING_APPOINTMENT: ConversationStage.OFFERING_TIMES,
            EnhancedStage.BOOKING_APPOINTMENT: ConversationStage.WAITING_FOR_TIME_SELECTION,
            EnhancedStage.COMPLETED: ConversationStage.COMPLETED
        }
        return mapping.get(enhanced_stage, ConversationStage.GREETING)
    
    def _determine_next_action(self, enhanced_analysis: Dict[str, Any]) -> str:
        """Determine next action based on enhanced analysis"""
        stage = enhanced_analysis["current_stage"]
        next_q = enhanced_analysis["next_question_to_ask"]
        
        # Map next question to action
        if next_q == "name":
            return "SEND_GREETING" if stage == EnhancedStage.GREETING else "ASK_FOR_NAME"
        elif next_q == "business":
            return "ASK_FOR_BUSINESS"
        elif next_q == "challenge":
            return "ASK_FOR_PROBLEM"
        elif next_q == "budget":
            return "ASK_FOR_BUDGET"
        elif next_q == "email":
            return "ASK_FOR_EMAIL"
        elif next_q == "appointment_time":
            return "OFFER_APPOINTMENT_TIMES"
        elif enhanced_analysis["expecting_answer_for"]:
            return f"PROCESS_{enhanced_analysis['expecting_answer_for'].upper()}"
        
        return "SEND_GREETING"
    
    def _set_allowed_response(self, analysis: Dict[str, Any]):
        """Set the EXACT response allowed for current stage"""
        stage = analysis["current_stage"]
        lang = analysis["language"]
        data = analysis["collected_data"]
        
        if stage in self.STAGE_TEMPLATES:
            template = self.STAGE_TEMPLATES[stage][lang]
            
            # Special handling for appointment tool stage
            if template == "USE_APPOINTMENT_TOOL":
                analysis["allowed_response"] = "USE_APPOINTMENT_TOOL"
                return
            
            # Fill in template with collected data
            if "{name}" in template and data["name"]:
                template = template.replace("{name}", data["name"])
            if "{business}" in template and data["business"]:
                template = template.replace("{business}", data["business"])
            if "{email}" in template and data["email"]:
                template = template.replace("{email}", data["email"])
                
            analysis["allowed_response"] = template
    
    def _get_forbidden_actions(self, analysis: Dict[str, Any]) -> List[str]:
        """Get list of forbidden actions for current stage"""
        forbidden = [
            "DO NOT ask questions out of order",
            "DO NOT skip any required questions",
            "DO NOT add extra questions",
            "DO NOT use pre-populated contact data",
            "DO NOT repeat questions already answered",
            "DO NOT greet again after initial greeting",
            "DO NOT say 'Hola [name]' if you already asked for name",
            "DO NOT confuse business type with customer name",
            "DO NOT ask about 'objetivo' or goals after problem",
            "DO NOT continue if budget not confirmed for warm/hot leads"
        ]
        
        # Stage-specific forbidden actions
        stage = analysis["current_stage"]
        if stage == ConversationStage.WAITING_FOR_NAME:
            forbidden.append("DO NOT say anything except 'Mucho gusto' after getting name")
        elif stage == ConversationStage.WAITING_FOR_BUSINESS:
            forbidden.append("DO NOT say 'Mucho gusto, [business]' - that's not their name!")
        
        return forbidden
    
    def get_exact_response(self, analysis: Dict[str, Any], agent_name: str) -> str:
        """
        Get the EXACT response the agent should send
        This is the ONLY response allowed - no variations!
        """
        # Check if agent is appropriate for this conversation
        score = analysis.get("lead_score", 0)
        budget_confirmed = analysis["collected_data"]["budget_confirmed"]
        
        # Route checks
        if agent_name == "maria" and score >= 5:
            return "ESCALATE:wrong_agent:Score is 5+, I only handle 1-4"
        elif agent_name == "maria" and budget_confirmed:
            return "ESCALATE:needs_qualification:Budget confirmed, needs Carlos"
        elif agent_name == "carlos" and score >= 8 and analysis["collected_data"]["email"]:
            return "ESCALATE:needs_appointment:Ready for appointment with Sofia"
        elif agent_name == "sofia" and not budget_confirmed:
            return "ESCALATE:needs_qualification:Budget not confirmed, needs Carlos"
        
        # Return the allowed response
        return analysis["allowed_response"] or "ESCALATE:customer_confused:Unexpected conversation state"
    
    def validate_agent_response(self, response: str, analysis: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that agent response follows rules
        Returns (is_valid, error_message)
        """
        allowed = analysis["allowed_response"]
        
        # Check for exact match (with some flexibility for punctuation)
        response_clean = response.strip().lower()
        allowed_clean = allowed.strip().lower() if allowed else ""
        
        # Check for forbidden patterns
        forbidden_patterns = [
            (r"¿cuál es tu objetivo", "Cannot ask about objectives"),
            (r"hola\s+\w+.*ayudo", "Cannot repeat greeting after name"),
            (r"mucho gusto.*restaurante", "Cannot use business as name"),
        ]
        
        for pattern, error in forbidden_patterns:
            if re.search(pattern, response_clean):
                return False, f"FORBIDDEN: {error}"
        
        # Allow close matches but log differences
        if response_clean != allowed_clean:
            logger.warning(f"Response differs from template: '{response}' vs '{allowed}'")
            
        return True, ""
    
    def get_conversation_summary(self, analysis: Dict[str, Any]) -> str:
        """Get human-readable summary of conversation state"""
        stage = analysis["current_stage"]
        data = analysis["collected_data"]
        
        summary = f"""
CONVERSATION STATE:
- Stage: {stage.value}
- Name: {data['name'] or 'NOT COLLECTED'}
- Business: {data['business'] or 'NOT COLLECTED'}
- Problem: {data['problem'] or 'NOT COLLECTED'}
- Budget OK: {'YES' if data['budget_confirmed'] else 'NO'}
- Email: {data['email'] or 'NOT COLLECTED'}
- Next Action: {analysis['next_action']}
- Language: {analysis['language'].upper()}
"""
        return summary


# Singleton instance
conversation_enforcer = ConversationEnforcer()


# Helper functions for agents
def get_conversation_analysis(messages: List[BaseMessage]) -> Dict[str, Any]:
    """Analyze conversation and return structured analysis"""
    return conversation_enforcer.analyze_conversation(messages)


def get_next_response(messages: List[BaseMessage], agent_name: str) -> str:
    """Get the EXACT response the agent should send"""
    analysis = get_conversation_analysis(messages)
    return conversation_enforcer.get_exact_response(analysis, agent_name)


def validate_response(response: str, messages: List[BaseMessage]) -> Tuple[bool, str]:
    """Validate that response follows conversation rules"""
    analysis = get_conversation_analysis(messages)
    return conversation_enforcer.validate_agent_response(response, analysis)