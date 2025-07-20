"""
Intelligence Analyzer - Pre-processing layer for structured extraction and scoring
Combines rule-based extraction with LLM analysis for optimal lead qualification
UPDATED: Optimized for Python 3.13 JIT compilation with cached regex patterns
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from functools import lru_cache
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.types import Command
from app.state.conversation_state import ConversationState
from app.utils.simple_logger import get_logger

logger = get_logger("intelligence_analyzer")


class SpanishPatternExtractor:
    """Extract structured information from Spanish messages using patterns
    
    Optimized for Python 3.13 JIT compilation with compiled regex patterns
    """
    
    def __init__(self):
        # Pre-compile all regex patterns for JIT optimization
        self._compiled_patterns = self._compile_all_patterns()
    
    @staticmethod
    @lru_cache(maxsize=1)
    def _compile_all_patterns() -> Dict[str, List[Tuple]]:
        """Compile all regex patterns once - JIT optimized"""
        return {
            "name": [
                (re.compile(r'\b(?:soy|me llamo|mi nombre es)\s+([A-Za-zÀ-ÿ]+)', re.IGNORECASE), 'explicit'),
                (re.compile(r'\b([A-Za-zÀ-ÿ]+)\s+y\s+tengo', re.IGNORECASE), 'contextual'),
                (re.compile(r'(?:hola|buenos días|buenas tardes),?\s*(?:soy|me llamo)\s+([A-Za-zÀ-ÿ]+)', re.IGNORECASE), 'greeting'),
                (re.compile(r'\b([A-Za-zÀ-ÿ]+)\s*@', re.IGNORECASE), 'email_prefix'),
            ],
            "business": [
                (re.compile(r'\b(?:tengo un|tengo una|tengo u\.)\s+([A-Za-zÀ-ÿ]+)(?:\s+(?:y|que|donde)|\s*[,.]|$)', re.IGNORECASE), 'possession'),
                (re.compile(r'\bmi\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})(?:\s+(?:es|está|tiene)|\s*[,.]|$)', re.IGNORECASE), 'possession'),
                (re.compile(r'\b(?:trabajo en|soy dueño de|manejo un)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})', re.IGNORECASE), 'occupation'),
                (re.compile(r'\b(restaurante|restaurant|negocio|empresa|tienda|local|clínica|consultorio|agencia|estudio|taller)\b', re.IGNORECASE), 'business_type'),
            ],
            "budget": [
                (re.compile(r'como unos?\s*\$?\s*(\d+)', re.IGNORECASE), '{0}', 'approximate'),
                (re.compile(r'aproximadamente\s*\$?\s*(\d+)', re.IGNORECASE), '{0}', 'approximate'),
                (re.compile(r'alrededor de\s*\$?\s*(\d+)', re.IGNORECASE), '{0}', 'approximate'),
                (re.compile(r'más o menos\s*\$?\s*(\d+)', re.IGNORECASE), '{0}', 'approximate'),
                (re.compile(r'unos?\s*\$?\s*(\d+)', re.IGNORECASE), '{0}', 'approximate'),
                (re.compile(r'(\d+)\s*más o menos', re.IGNORECASE), '{0}', 'approximate'),
                (re.compile(r'entre\s*\$?\s*(\d+)\s*y\s*\$?\s*(\d+)', re.IGNORECASE), '{0}-{1}', 'range'),
                (re.compile(r'(\d+)\s*o más', re.IGNORECASE), '{0}+', 'minimum'),
                (re.compile(r'hasta\s*\$?\s*(\d+)', re.IGNORECASE), 'up to {0}', 'maximum'),
                (re.compile(r'máximo\s*\$?\s*(\d+)', re.IGNORECASE), 'max {0}', 'maximum'),
                (re.compile(r'\$?\s*(\d+)\s*(?:al mes|mensuales?|por mes)', re.IGNORECASE), '{0}/month', 'monthly'),
                (re.compile(r'(?:^|\s)\$?\s*(\d+)\s*(?:$|\s)', re.IGNORECASE), '{0}', 'direct'),
            ],
            "goal": [
                (re.compile(r'(?:necesito|quiero|busco|requiero)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'need'),
                (re.compile(r'(?:mi problema es|tengo problemas con)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'problem'),
                (re.compile(r'(?:estoy perdiendo|perdiendo)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'problem'),
                (re.compile(r'no puedo\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'problem'),
                (re.compile(r'(?:para|con el fin de)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'purpose'),
                (re.compile(r'(?:automatizar|mejorar|aumentar|crecer)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'action'),
            ],
            "email": [
                (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 'email')
            ],
            "phone": [
                (re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'), '123-456-7890'),
                (re.compile(r'\b\d{10}\b'), '1234567890'),
                (re.compile(r'\b\+?1?\s*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})\b'), 'various'),
            ]
        }
    
    def extract_all(self, message: str, conversation_history: List[str] = None) -> Dict[str, Any]:
        """Extract all structured information from message and history"""
        conversation_history = conversation_history or []
        full_text = " ".join([message] + conversation_history[-10:])  # Last 10 messages for context
        
        extracted = {
            "name": self._extract_name(full_text),
            "business_type": self._extract_business(full_text),
            "budget": self._extract_budget(full_text),
            "goal": self._extract_goal(full_text),
            "email": self._extract_email(full_text),
            "phone": self._extract_phone(full_text),
            "extraction_confidence": {}
        }
        
        # Add confidence scores
        for field, value in extracted.items():
            if field != "extraction_confidence" and value:
                extracted["extraction_confidence"][field] = self._calculate_confidence(value, full_text)
        
        return extracted
    
    @lru_cache(maxsize=512)  # Cache results for JIT optimization
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract name from text - JIT optimized with caching"""
        for pattern, confidence_type in self._compiled_patterns["name"]:
            match = pattern.search(text)
            if match:
                name = match.group(1).strip()
                # Validate name (not common words)
                if name.lower() not in ['un', 'una', 'el', 'la', 'mi', 'tu']:
                    return name.title()
        return None
    
    @lru_cache(maxsize=512)  # Cache results for JIT optimization
    def _extract_business(self, text: str) -> Optional[str]:
        """Extract business type from text - JIT optimized"""
        for pattern, confidence_type in self._compiled_patterns["business"]:
            match = pattern.search(text)
            if match:
                business = match.group(1).strip()
                # Clean common words
                business = re.sub(r'\b(un|una|el|la|mi)\b', '', business).strip()
                if business:
                    return business.lower()
        return None
    
    @lru_cache(maxsize=512)  # Cache results for JIT optimization
    def _extract_budget(self, text: str) -> Optional[str]:
        """Extract budget information from text - JIT optimized"""
        for pattern_data in self._compiled_patterns["budget"]:
            if len(pattern_data) == 3:
                pattern, format_str, budget_type = pattern_data
            else:
                pattern, budget_type = pattern_data
                format_str = '{0}'
            
            match = pattern.search(text)
            if match:
                # Format the budget string
                groups = match.groups()
                budget = format_str
                for i, group in enumerate(groups):
                    budget = budget.replace(f'{{{i}}}', group)
                return budget
        return None
    
    @lru_cache(maxsize=512)  # Cache results for JIT optimization
    def _extract_goal(self, text: str) -> Optional[str]:
        """Extract goals or problems from text - JIT optimized"""
        for pattern, goal_type in self._compiled_patterns["goal"]:
            match = pattern.search(text)
            if match:
                goal = match.group(1).strip()
                if len(goal) > 10:  # Meaningful goal
                    return goal
        return None
    
    @lru_cache(maxsize=512)  # Cache results for JIT optimization
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text - JIT optimized"""
        for pattern, _ in self._compiled_patterns["email"]:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None
    
    @lru_cache(maxsize=512)  # Cache results for JIT optimization
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text - JIT optimized"""
        for pattern, _ in self._compiled_patterns["phone"]:
            match = pattern.search(text)
            if match:
                # Clean and standardize
                phone = re.sub(r'\D', '', match.group(0))
                if len(phone) >= 10:
                    return phone
        return None
    
    def _calculate_confidence(self, value: str, full_text: str) -> float:
        """Calculate extraction confidence (0-1)"""
        # Higher confidence if value appears multiple times
        occurrences = len(re.findall(re.escape(value), full_text, re.IGNORECASE))
        base_confidence = 0.6
        
        if occurrences > 1:
            base_confidence += 0.2
        if len(value) > 20:  # Longer extractions might be less accurate
            base_confidence -= 0.1
            
        return min(1.0, max(0.0, base_confidence))


class LeadScorer:
    """Calculate lead score based on extracted information and rules"""
    
    def calculate_score(self, 
                       extracted_data: Dict[str, Any], 
                       previous_score: int = 0,
                       conversation_length: int = 0) -> Tuple[int, str, Dict[str, int]]:
        """
        Calculate lead score (1-10) based on extracted data
        
        Returns:
            score: int (1-10)
            reasoning: str
            score_breakdown: Dict[str, int]
        """
        score_breakdown = {
            "base": 1,
            "name": 0,
            "business": 0,
            "goal": 0,
            "budget": 0,
            "email": 0,
            "phone": 0,
            "engagement": 0
        }
        
        reasoning_parts = []
        
        # Name: 1-2 points
        if extracted_data.get("name"):
            score_breakdown["name"] = 2
            reasoning_parts.append("has name")
        
        # Business: 1-2 points
        if extracted_data.get("business_type"):
            score_breakdown["business"] = 2
            reasoning_parts.append(f"has business ({extracted_data['business_type']})")
        
        # Goal/Problem: 1-2 points
        if extracted_data.get("goal"):
            score_breakdown["goal"] = 2
            reasoning_parts.append("has clear goal/problem")
        
        # Budget: 2-3 points
        if extracted_data.get("budget"):
            budget_str = str(extracted_data["budget"])
            # Check if budget is substantial
            if any(x in budget_str for x in ["300", "400", "500"]) or \
               re.search(r'\d{3,}', budget_str):  # 3+ digit number
                score_breakdown["budget"] = 3
                reasoning_parts.append(f"has substantial budget ({budget_str})")
            else:
                score_breakdown["budget"] = 2
                reasoning_parts.append(f"has budget ({budget_str})")
        
        # Contact info: 1 point each
        if extracted_data.get("email"):
            score_breakdown["email"] = 1
            reasoning_parts.append("provided email")
            
        if extracted_data.get("phone"):
            score_breakdown["phone"] = 1
            reasoning_parts.append("provided phone")
        
        # Engagement bonus: up to 1 point
        if conversation_length > 5:
            score_breakdown["engagement"] = 1
            reasoning_parts.append("engaged conversation")
        
        # Calculate total
        total_score = sum(score_breakdown.values())
        
        # Apply score persistence rule (never decrease)
        final_score = max(total_score, previous_score)
        
        if final_score > total_score:
            reasoning_parts.append(f"maintained previous score ({previous_score})")
        
        # Cap at 10
        final_score = min(10, final_score)
        
        reasoning = f"Score {final_score}: " + ", ".join(reasoning_parts) if reasoning_parts else "minimal information"
        
        return final_score, reasoning, score_breakdown


class BudgetConfirmationDetector:
    """Detect budget confirmations in context"""
    
    CONFIRMATION_WORDS = [
        "si", "sí", "yes", "claro", "por supuesto", "ok", "dale", 
        "está bien", "me parece bien", "correcto", "exacto", "perfecto"
    ]
    
    BUDGET_MENTIONS = [
        r'\$?\s*300', r'300\s*al\s*mes', r'trescientos',
        r'\$?\s*400', r'400\s*al\s*mes', r'cuatrocientos',
        r'\$?\s*500', r'500\s*al\s*mes', r'quinientos'
    ]
    
    def detect_confirmation(self, 
                           current_message: str, 
                           last_assistant_message: str) -> Dict[str, Any]:
        """Detect if current message confirms a budget mentioned previously"""
        
        current_lower = current_message.lower().strip()
        
        # Check if it's a simple confirmation
        is_confirmation = any(word == current_lower for word in self.CONFIRMATION_WORDS)
        
        if not is_confirmation:
            return {"budget_confirmed": False}
        
        # Check if last assistant message mentioned budget
        budget_amount = None
        for pattern in self.BUDGET_MENTIONS:
            if re.search(pattern, last_assistant_message, re.IGNORECASE):
                # Extract the numeric value
                match = re.search(r'(\d+)', pattern)
                if match:
                    budget_amount = match.group(1) + "+"
                    break
        
        if budget_amount:
            return {
                "budget_confirmed": True,
                "amount": budget_amount,
                "confidence": 0.9,
                "boost_score": True
            }
        
        return {"budget_confirmed": False}


class IntelligenceAnalyzer:
    """Main analyzer that combines all extraction and scoring components"""
    
    def __init__(self):
        self.extractor = SpanishPatternExtractor()
        self.scorer = LeadScorer()
        self.budget_detector = BudgetConfirmationDetector()
        
    async def analyze(self, state: ConversationState) -> Dict[str, Any]:
        """
        Analyze conversation and extract intelligence
        
        Returns enriched state with:
        - extracted_data
        - lead_score
        - score_history
        - routing_suggestion
        - analysis_metadata
        """
        # Get conversation context
        messages = state.get("messages", [])
        if not messages:
            return state
        
        # Trim messages if too long to prevent token overflow
        from app.utils.message_utils import get_trimmed_messages
        messages = get_trimmed_messages(messages, config_name="extended")
            
        current_message = messages[-1].content if messages else ""
        # Extract ALL conversation history for better context
        conversation_history = [m.content for m in messages if hasattr(m, 'content')]
        
        # Get previous score
        previous_score = state.get("lead_score", 0)
        
        # Extract structured data
        extracted = self.extractor.extract_all(current_message, conversation_history)
        
        # Initialize budget_confirmation
        budget_confirmation = {}
        
        # Check for budget confirmation
        if len(messages) >= 2:
            last_assistant_msg = ""
            for msg in reversed(messages[:-1]):
                if isinstance(msg, AIMessage):
                    last_assistant_msg = msg.content
                    break
                    
            budget_confirmation = self.budget_detector.detect_confirmation(
                current_message, last_assistant_msg
            )
            
            if budget_confirmation.get("budget_confirmed"):
                extracted["budget"] = budget_confirmation["amount"]
                
        # Merge with existing data
        existing_data = state.get("extracted_data", {})
        for key, value in extracted.items():
            if value and not existing_data.get(key):
                existing_data[key] = value
                
        # Calculate score
        score, reasoning, breakdown = self.scorer.calculate_score(
            existing_data, 
            previous_score,
            len(messages)
        )
        
        # Boost score for budget confirmation
        if budget_confirmation.get("boost_score") and score < 6:
            score = 6
            reasoning += " - budget confirmed, upgraded to warm lead"
            
        # Determine routing
        if score >= 8:
            route = "hot"
            suggested_agent = "sofia"
        elif score >= 5:
            route = "warm"
            suggested_agent = "carlos"
        else:
            route = "cold"
            suggested_agent = "maria"
            
        # Build analysis metadata
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "message_analyzed": current_message[:100] + "..." if len(current_message) > 100 else current_message,
            "extraction_method": "rule_based",
            "confidence_scores": extracted.get("extraction_confidence", {}),
            "score_breakdown": breakdown
        }
        
        # Update score history
        score_history = state.get("score_history", [])
        score_history.append({
            "score": score,
            "previous_score": previous_score,
            "timestamp": datetime.now().isoformat(),
            "reasoning": reasoning,
            "trigger": "message_analysis"
        })
        
        # Return enriched state
        return {
            **state,
            "extracted_data": existing_data,
            "lead_score": score,
            "lead_category": route,
            "suggested_agent": suggested_agent,
            "score_history": score_history,
            "analysis_metadata": analysis,
            "score_reasoning": reasoning
        }


# Create node for LangGraph workflow
async def intelligence_node(state: ConversationState) -> Dict[str, Any]:
    """Intelligence analysis node for workflow"""
    from app.utils.tracing import log_feedback, TracedOperation
    analyzer = IntelligenceAnalyzer()
    
    try:
        # Run analysis with tracing
        async with TracedOperation(
            "intelligence_analysis",
            metadata={
                "contact_id": state.get("contact_id", "unknown"),
                "previous_score": state.get("lead_score", 0),
                "message_count": len(state.get("messages", []))
            },
            tags=["intelligence", "scoring", "extraction"]
        ):
            # Run analysis
            enriched_state = await analyzer.analyze(state)
        
        logger.info(
            f"Intelligence analysis complete: Score {enriched_state['lead_score']}, "
            f"Route: {enriched_state['lead_category']}, "
            f"Suggested: {enriched_state['suggested_agent']}"
        )
        
        # Log lead score as feedback for tracking
        if hasattr(TracedOperation, '_current_run_id'):
            log_feedback(
                run_id=TracedOperation._current_run_id,
                score=enriched_state['lead_score'] / 10.0,  # Normalize to 0-1
                feedback_type="lead_score",
                comment=enriched_state.get('score_reasoning')
            )
        
        return enriched_state
        
    except Exception as e:
        logger.error(f"Intelligence analysis failed: {str(e)}", exc_info=True)
        # Return state unchanged on error
        return state


__all__ = [
    "IntelligenceAnalyzer",
    "SpanishPatternExtractor", 
    "LeadScorer",
    "BudgetConfirmationDetector",
    "intelligence_node"
]