"""
Enhanced Conversation Analyzer - Properly tracks what's been asked and answered
Prevents agents from repeating questions
"""
from typing import Dict, Any, List, Optional, Set
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.state.enhanced_conversation_state import ConversationStage, ConversationAnalysis
from app.utils.simple_logger import get_logger
import re

logger = get_logger("conversation_analyzer")


class ConversationAnalyzer:
    """
    Analyzes conversation to track progress and prevent repetition
    This is the fix for agents asking the same questions multiple times
    """
    
    # Question patterns to detect what was asked
    QUESTION_PATTERNS = {
        "name": [
            r"¿cuál es tu nombre\?",
            r"what'?s your name\?",
            r"¿cómo te llamas\?",
            r"who am i speaking with\?"
        ],
        "business": [
            r"¿qué tipo de negocio",
            r"what type of business",
            r"what industry",
            r"¿en qué trabajas\?"
        ],
        "challenge": [
            r"¿cuál es tu mayor desafío",
            r"biggest challenge",
            r"what'?s taking most of your time",
            r"¿qué problema"
        ],
        "budget": [
            r"\$\d+",
            r"presupuesto",
            r"budget",
            r"inversión",
            r"investment"
        ],
        "email": [
            r"correo electrónico",
            r"email",
            r"enviar.*enlace",
            r"send.*link"
        ]
    }
    
    # Answer patterns to detect responses
    ANSWER_PATTERNS = {
        "budget_confirmation": [
            r"^(sí|si|yes|claro|ok|perfecto|dale|va|bueno)$",
            r"me parece bien",
            r"está bien",
            r"sounds good"
        ],
        "budget_rejection": [
            r"^(no|nope|para nada|muy caro|expensive)$",
            r"no puedo",
            r"es mucho",
            r"too much"
        ]
    }
    
    @classmethod
    def analyze_conversation(cls, messages: List[BaseMessage]) -> ConversationAnalysis:
        """
        Analyze conversation to determine state and prevent repetition
        """
        analysis: ConversationAnalysis = {
            "current_stage": ConversationStage.GREETING,
            "collected_data": {
                "name": None,
                "business_type": None,
                "challenge": None,
                "budget_confirmed": False,
                "budget_amount": None,
                "email": None
            },
            "questions_asked": set(),
            "expecting_answer_for": None,
            "next_question_to_ask": None,
            "can_skip_to": None,
            "language": "es",
            "last_human_message": None,
            "last_ai_question": None,
            "conversation_summary": ""
        }
        
        # Track what we're expecting an answer for
        currently_expecting = None
        
        # Analyze messages in chronological order
        for i, msg in enumerate(messages):
            content = msg.content.lower() if hasattr(msg, 'content') else ""
            
            # Skip system messages and empty content
            if not content or (hasattr(msg, 'type') and msg.type == "system"):
                continue
                
            # AI/Assistant messages - track what was asked
            if isinstance(msg, AIMessage) or (hasattr(msg, 'role') and msg.role == "assistant"):
                # Check what question was asked
                for question_type, patterns in cls.QUESTION_PATTERNS.items():
                    if any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns):
                        analysis["questions_asked"].add(question_type)
                        currently_expecting = question_type
                        analysis["last_ai_question"] = question_type
                        logger.info(f"AI asked about: {question_type}")
                        break
                        
            # Human messages - extract answers
            elif isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == "human"):
                analysis["last_human_message"] = content
                
                # Check if this is a historical message
                is_historical = False
                if hasattr(msg, 'additional_kwargs'):
                    is_historical = msg.additional_kwargs.get('source') == 'ghl_history'
                
                # For historical messages, we still want to extract data!
                # This fixes the context blindness issue
                
                # Detect language ONLY from current customer message, not historical
                # This prevents the system from switching to English when agents respond
                if not is_historical:
                    # Only detect language from the current human message
                    # More sophisticated detection: check for Spanish patterns first
                    spanish_indicators = ["hola", "gracias", "por favor", "buenas", "días", "tardes", 
                                        "qué", "cómo", "cuál", "dónde", "cuándo", "quiero", "necesito",
                                        "tengo", "estoy", "perdiendo", "restaurante", "negocio"]
                    english_indicators = ["hello", "hi", "thanks", "please", "good morning", "good afternoon",
                                        "what", "how", "which", "where", "when", "want", "need",
                                        "have", "i'm", "losing", "restaurant", "business"]
                    
                    # Count indicators
                    spanish_count = sum(1 for word in spanish_indicators if word in content)
                    english_count = sum(1 for word in english_indicators if word in content)
                    
                    # Only change language if strong evidence (and default to Spanish)
                    if english_count > spanish_count and english_count >= 2:
                        analysis["language"] = "en"
                    else:
                        # Default to Spanish or keep existing language
                        analysis["language"] = "es"
                
                # Process answers - include historical context
                # We MUST process historical messages to understand what data we already have!
                if currently_expecting:
                    logger.info(f"Processing answer for: {currently_expecting}, content: '{content}'")
                    
                    if currently_expecting == "name":
                        # The entire message is their name (unless it's a greeting)
                        if content.strip() not in ["hola", "hi", "hello", "buenos días", "buenas tardes"]:
                            analysis["collected_data"]["name"] = content.strip().title()
                            currently_expecting = None
                            logger.info(f"Collected name: {analysis['collected_data']['name']}")
                            
                    elif currently_expecting == "business":
                        # The entire message is their business type
                        analysis["collected_data"]["business_type"] = content.strip()
                        currently_expecting = None
                        logger.info(f"Collected business: {analysis['collected_data']['business_type']}")
                        
                    elif currently_expecting == "challenge":
                        # Any response is their challenge
                        analysis["collected_data"]["challenge"] = content.strip()
                        currently_expecting = None
                        logger.info(f"Collected challenge: {analysis['collected_data']['challenge']}")
                        
                    elif currently_expecting == "budget":
                        # Check for budget confirmation
                        if any(re.search(pattern, content, re.IGNORECASE) for pattern in cls.ANSWER_PATTERNS["budget_confirmation"]):
                            analysis["collected_data"]["budget_confirmed"] = True
                            analysis["collected_data"]["budget_amount"] = "300+"
                            currently_expecting = None
                            logger.info("Budget confirmed")
                        elif any(re.search(pattern, content, re.IGNORECASE) for pattern in cls.ANSWER_PATTERNS["budget_rejection"]):
                            analysis["collected_data"]["budget_confirmed"] = False
                            currently_expecting = None
                            logger.info("Budget rejected")
                            
                    elif currently_expecting == "email":
                        # Check for email pattern
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                        if email_match:
                            analysis["collected_data"]["email"] = email_match.group(0)
                            currently_expecting = None
                            logger.info(f"Collected email: {analysis['collected_data']['email']}")
        
        # Set what we're expecting if still waiting
        analysis["expecting_answer_for"] = currently_expecting
        
        # Determine current stage and next action
        analysis = cls._determine_stage_and_next_action(analysis)
        
        # Generate conversation summary
        analysis["conversation_summary"] = cls._generate_summary(analysis)
        
        return analysis
    
    @classmethod
    def _determine_stage_and_next_action(cls, analysis: ConversationAnalysis) -> ConversationAnalysis:
        """Determine current stage and what to do next"""
        data = analysis["collected_data"]
        asked = analysis["questions_asked"]
        
        # Determine stage based on what we have and what we've asked
        if not asked:
            # Haven't asked anything yet
            analysis["current_stage"] = ConversationStage.GREETING
            analysis["next_question_to_ask"] = "name"
            
        elif "name" in asked and not data["name"]:
            # Asked for name, waiting for answer
            analysis["current_stage"] = ConversationStage.COLLECTING_NAME
            analysis["expecting_answer_for"] = "name"
            
        elif data["name"] and "business" not in asked:
            # Have name, need to ask for business
            analysis["current_stage"] = ConversationStage.COLLECTING_NAME
            analysis["next_question_to_ask"] = "business"
            
        elif "business" in asked and not data["business_type"]:
            # Asked for business, waiting for answer
            analysis["current_stage"] = ConversationStage.COLLECTING_BUSINESS
            analysis["expecting_answer_for"] = "business"
            
        elif data["business_type"] and "challenge" not in asked:
            # Have business, need to ask for challenge
            analysis["current_stage"] = ConversationStage.COLLECTING_BUSINESS
            analysis["next_question_to_ask"] = "challenge"
            
        elif "challenge" in asked and not data["challenge"]:
            # Asked for challenge, waiting for answer
            analysis["current_stage"] = ConversationStage.COLLECTING_CHALLENGE
            analysis["expecting_answer_for"] = "challenge"
            
        elif data["challenge"] and "budget" not in asked:
            # Have challenge, need to ask for budget
            analysis["current_stage"] = ConversationStage.COLLECTING_CHALLENGE
            analysis["next_question_to_ask"] = "budget"
            
        elif "budget" in asked and data["budget_confirmed"] is None:
            # Asked for budget, waiting for answer
            analysis["current_stage"] = ConversationStage.COLLECTING_BUDGET
            analysis["expecting_answer_for"] = "budget"
            
        elif data["budget_confirmed"] and "email" not in asked:
            # Budget confirmed, need email
            analysis["current_stage"] = ConversationStage.COLLECTING_BUDGET
            analysis["next_question_to_ask"] = "email"
            
        elif "email" in asked and not data["email"]:
            # Asked for email, waiting for answer
            analysis["current_stage"] = ConversationStage.COLLECTING_EMAIL
            analysis["expecting_answer_for"] = "email"
            
        elif data["email"]:
            # Have everything, ready for appointment
            analysis["current_stage"] = ConversationStage.OFFERING_APPOINTMENT
            analysis["next_question_to_ask"] = "appointment_time"
        
        # Check if we can skip ahead (user provided multiple pieces of info)
        if not data["name"] and analysis["last_human_message"]:
            # Check if message contains a name pattern
            name_match = re.search(r"(?:me llamo|mi nombre es|soy)\s+(\w+)", analysis["last_human_message"])
            if name_match:
                data["name"] = name_match.group(1).title()
                analysis["can_skip_to"] = "business"
        
        return analysis
    
    @classmethod
    def _generate_summary(cls, analysis: ConversationAnalysis) -> str:
        """Generate a summary of the conversation state"""
        data = analysis["collected_data"]
        asked = analysis["questions_asked"]
        
        summary_parts = []
        
        if data["name"]:
            summary_parts.append(f"Customer: {data['name']}")
        
        if data["business_type"]:
            summary_parts.append(f"Business: {data['business_type']}")
            
        if data["challenge"]:
            summary_parts.append(f"Challenge: {data['challenge'][:50]}...")
            
        if data["budget_confirmed"]:
            summary_parts.append("Budget: Confirmed ($300+)")
        elif data["budget_confirmed"] is False:
            summary_parts.append("Budget: Rejected")
            
        if data["email"]:
            summary_parts.append(f"Email: {data['email']}")
        
        if asked:
            summary_parts.append(f"Questions asked: {', '.join(sorted(asked))}")
            
        if analysis["expecting_answer_for"]:
            summary_parts.append(f"Waiting for: {analysis['expecting_answer_for']}")
        
        return " | ".join(summary_parts) if summary_parts else "New conversation"