"""
Intelligence Analyzer - Pre-processing layer for structured extraction and scoring
Combines rule-based extraction with LLM analysis for optimal lead qualification
UPDATED: Optimized for Python 3.13 JIT compilation with cached regex patterns
ENHANCED: Added fuzzy matching for typo tolerance
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from functools import lru_cache
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.types import Command
from app.state.minimal_state import MinimalState
from app.utils.simple_logger import get_logger

logger = get_logger("intelligence_analyzer")

# Try to import fuzzy extractor, fallback if not available
FuzzyBusinessExtractor = None
FUZZY_ENABLED = False

try:
    from app.intelligence.fuzzy_extractor import FuzzyBusinessExtractor
    FUZZY_ENABLED = True
    logger.info("Fuzzy extractor loaded successfully")
except ImportError as e:
    logger.warning(f"Fuzzy extractor not available (likely rapidfuzz not installed): {str(e)}")
    # Create a dummy class to prevent AttributeError
    class FuzzyBusinessExtractor:
        def extract_with_context(self, text: str):
            return None
except Exception as e:
    logger.error(f"Unexpected error loading fuzzy extractor: {str(e)}")
    # Create a dummy class to prevent AttributeError
    class FuzzyBusinessExtractor:
        def extract_with_context(self, text: str):
            return None


class SpanishPatternExtractor:
    """Extract structured information from Spanish messages using patterns
    
    Optimized for Python 3.13 JIT compilation with compiled regex patterns
    Enhanced with fuzzy matching for typo tolerance
    """
    
    def __init__(self):
        # Pre-compile all regex patterns for JIT optimization
        self._compiled_patterns = self._compile_all_patterns()
        
        # Initialize fuzzy extractor if available
        self.fuzzy_extractor = None
        if FUZZY_ENABLED and FuzzyBusinessExtractor:
            try:
                self.fuzzy_extractor = FuzzyBusinessExtractor()
                logger.info("Fuzzy extractor initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize fuzzy extractor: {str(e)}")
                self.fuzzy_extractor = None
    
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
                # Pattern for single word that looks like a name (3+ letters, capitalized)
                (re.compile(r'^([A-Z][a-zÀ-ÿ]{2,})$'), 'single_name'),
            ],
            "business": [
                # Pattern 1: "tengo un/una X" but exclude generic terms in capture
                (re.compile(r'\b(?:tengo un|tengo una|tengo u\.)\s+(?!negocio|empresa|local|comercio)([A-Za-zÀ-ÿ]+)(?:\s+(?:y|que|donde)|\s*[,.]|$)', re.IGNORECASE), 'possession'),
                # Pattern 2: "mi X" but exclude generic terms in capture
                (re.compile(r'\bmi\s+(?!negocio|empresa|local|comercio)([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})(?:\s+(?:es|está|tiene)|\s*[,.]|$)', re.IGNORECASE), 'possession'),
                # Pattern 3: occupation patterns
                (re.compile(r'\b(?:trabajo en|soy dueño de|manejo un)\s+(?!negocio|empresa|local|comercio)([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})', re.IGNORECASE), 'occupation'),
                # Pattern 4: Direct business type mentions (specific businesses only)
                (re.compile(r'\b(restaurante|restaurant|tienda|clínica|consultorio|agencia|estudio|taller|barbería|barberia|salon|salón|cafetería|cafeteria|hotel|spa|gimnasio|gym|pizzeria|bar|club|panadería|farmacia|estética|dentista|peluquería|boutique|catering)\b', re.IGNORECASE), 'business_type'),
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
    
    def extract_all(self, message: str, previous_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract structured information from CURRENT message only
        
        Args:
            message: Current message to analyze
            previous_data: Previously extracted data to merge with
            
        Returns:
            Extracted data from current message merged with previous data
        """
        previous_data = previous_data or {}
        
        # Extract from CURRENT MESSAGE ONLY
        # CRITICAL: This prevents agents from using old conversation history incorrectly
        # We extract from the current message and OVERWRITE with new data when found
        extracted = {
            "name": self._extract_name(message) if self._extract_name(message) else previous_data.get("name"),
            "business_type": self._extract_business(message) if self._extract_business(message) else previous_data.get("business_type"),
            "budget": self._extract_budget(message) if self._extract_budget(message) else previous_data.get("budget"),
            "goal": self._extract_goal(message) if self._extract_goal(message) else previous_data.get("goal"),
            "email": self._extract_email(message) if self._extract_email(message) else previous_data.get("email"),
            "phone": self._extract_phone(message) if self._extract_phone(message) else previous_data.get("phone"),
            "extraction_confidence": {}
        }
        
        # Add confidence scores only for newly extracted data
        MIN_CONFIDENCE = 0.7  # Confidence threshold
        
        for field, value in extracted.items():
            if field != "extraction_confidence" and value:
                # Only add confidence if newly extracted (not from previous)
                if value != previous_data.get(field):
                    confidence = self._calculate_confidence(value, message)
                    
                    # Only keep extraction if confidence is high enough
                    if confidence >= MIN_CONFIDENCE:
                        extracted["extraction_confidence"][field] = confidence
                    else:
                        # Low confidence - revert to previous value
                        extracted[field] = previous_data.get(field)
                        logger.info(f"Rejected low confidence extraction: {field}={value} (conf={confidence:.2f})")
        
        return extracted
    
    def _validate_business_type(self, business: str) -> Optional[str]:
        """Validate extracted business type"""
        if not business:
            return None
            
        # Remove common filler words
        business = business.lower().strip()
        
        # List of invalid business types
        invalid_patterns = [
            "negocio hola", "business hello", "mi hola", "un hola",
            "negocio si", "business yes", "negocio no", "hola"
        ]
        
        if business in invalid_patterns:
            return None
        
        # Check if it contains greeting words (invalid)
        greeting_words = ["hola", "hello", "hi", "hey", "buenos", "dias", "tardes", "noches"]
        for greeting in greeting_words:
            if greeting in business.split():
                return None
        
        # CRITICAL FIX: "negocio" alone is NOT a valid business type - it's too generic
        # Also exclude other generic terms
        generic_terms = ["negocio", "business", "empresa", "comercio", "local"]
        if business in generic_terms:
            logger.info(f"Rejecting generic business term: {business}")
            return None
        
        # Valid SPECIFIC business types
        valid_businesses = [
            "restaurante", "restaurant", "tienda", "salon", "salón",
            "barbería", "barberia", "clinica", "clínica", "consultorio",
            "agencia", "oficina", "cafetería", "cafeteria", "hotel", 
            "spa", "gimnasio", "gym", "boutique", "peluquería", 
            "pizzeria", "bar", "club", "panadería", "farmacia",
            "catering",  # Added catering to valid businesses
            "taller", "estética", "dentista"
        ]
        
        # Check if it contains at least one SPECIFIC business word
        has_valid = any(valid in business for valid in valid_businesses)
        
        if not has_valid:
            # Not a specific business type
            return None
        
        return business
    
    def _validate_budget(self, budget: str, message: str) -> Optional[str]:
        """Validate extracted budget"""
        if not budget:
            return None
        
        # Don't extract from time patterns
        time_pattern = r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)'
        if re.search(time_pattern, message):
            # Check if the number is part of a time
            if re.search(rf'{budget}:\d{{2}}', message):
                return None
        
        # Don't extract single/double digit numbers unless with currency
        if budget.isdigit() and len(budget) < 3:
            # Check if it has currency symbol nearby
            if not re.search(rf'\$\s*{budget}', message):
                return None
        
        # Don't extract from dates
        date_patterns = [
            rf'{budget}\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
            rf'{budget}/(0?[1-9]|1[0-2])',  # 10/5 (October 5th)
        ]
        for pattern in date_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return None
        
        return budget
    
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
        """Extract business type from text - JIT optimized with fuzzy fallback"""
        # First try exact pattern matching (fastest)
        for pattern, confidence_type in self._compiled_patterns["business"]:
            match = pattern.search(text)
            if match:
                business = match.group(1).strip()
                # Clean common words
                business = re.sub(r'\b(un|una|el|la|mi)\b', '', business).strip()
                
                # VALIDATE before returning
                validated = self._validate_business_type(business)
                if validated:
                    logger.info(f"Exact match found: {validated}")
                    return validated.lower()
        
        # If no exact match and fuzzy extractor is available, try fuzzy matching
        if self.fuzzy_extractor:
            logger.info("No exact match, trying fuzzy extraction...")
            fuzzy_result = self.fuzzy_extractor.extract_with_context(text)
            if fuzzy_result:
                business_type, confidence = fuzzy_result
                if confidence >= 0.75:  # High confidence threshold
                    logger.info(f"Fuzzy match found: {business_type} (confidence: {confidence:.2f})")
                    return business_type
                else:
                    logger.info(f"Low confidence fuzzy match: {business_type} ({confidence:.2f})")
        
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
                
                # VALIDATE before returning
                validated = self._validate_budget(budget, text)
                if validated:
                    return validated
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
        # Start with base confidence
        base_confidence = 0.7
        
        # Higher confidence if exact match (not substring)
        if re.search(rf'\b{re.escape(value)}\b', full_text, re.IGNORECASE):
            base_confidence += 0.1
        
        # Lower confidence for very short values
        if len(value) < 3:
            base_confidence -= 0.2
            
        # Higher confidence for values with clear context
        context_patterns = [
            rf'(?:soy|me llamo|mi nombre es)\s+{re.escape(value)}',  # Name
            rf'(?:tengo un|tengo una)\s+{re.escape(value)}',  # Business
            rf'\$\s*{re.escape(value)}',  # Budget with currency
        ]
        
        for pattern in context_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                base_confidence += 0.15
                break
                
        # Lower confidence for values that might be misextracted
        if value.lower() in ['si', 'no', 'hola', 'ok', 'bien']:
            base_confidence -= 0.3
            
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
        
        # Name: 1 point (more conservative)
        if extracted_data.get("name"):
            score_breakdown["name"] = 1
            reasoning_parts.append("has name")
        
        # Business: 2 points
        if extracted_data.get("business_type"):
            score_breakdown["business"] = 2
            reasoning_parts.append(f"has business ({extracted_data['business_type']})")
        
        # Goal/Problem: 1 point (reduced)
        if extracted_data.get("goal"):
            score_breakdown["goal"] = 1
            reasoning_parts.append("has goal/problem")
        
        # Budget: 1-3 points
        if extracted_data.get("budget"):
            budget_str = str(extracted_data["budget"])
            # Check if budget is substantial ($300+)
            if any(x in budget_str for x in ["300", "400", "500"]) or \
               re.search(r'\d{3,}', budget_str):  # 3+ digit number
                score_breakdown["budget"] = 3
                reasoning_parts.append(f"budget confirmed ({budget_str})")
            else:
                score_breakdown["budget"] = 1  # Reduced for unconfirmed budgets
                reasoning_parts.append(f"budget mentioned ({budget_str})")
        
        # Email: 1 point (only if not "none")
        if extracted_data.get("email") and extracted_data["email"] != "none":
            score_breakdown["email"] = 1
            reasoning_parts.append("has email")
            
        # Phone: 0 points (removed - phone comes from GHL automatically)
        # Not scoring phone anymore as it's not customer-provided
        
        # Engagement bonus: 1 point only for long conversations
        if conversation_length > 10:  # Increased threshold
            score_breakdown["engagement"] = 1
            reasoning_parts.append("highly engaged")
        
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
        
    async def analyze(self, state: MinimalState) -> Dict[str, Any]:
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
        
        # Get previous score and data
        previous_score = state.get("lead_score", 0)
        previous_data = state.get("extracted_data", {})
        
        # Extract from CURRENT MESSAGE ONLY, merge with previous
        # CRITICAL FIX: This ensures agents use the current state's extracted_data
        # NOT old conversation history. The extract_all method only extracts from
        # the current message and merges with previous_data to maintain state.
        # This prevents agents from being confused by old conversation context.
        extracted = self.extractor.extract_all(current_message, previous_data)
        
        # CRITICAL FIX: Never persist generic business terms
        # Even if they were extracted before our fix, remove them from state
        generic_terms = ["negocio", "empresa", "local", "comercio", "business"]
        if extracted.get("business_type") in generic_terms:
            logger.info(f"Removing generic business term from state: {extracted['business_type']}")
            extracted["business_type"] = None
        
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
                
        # Calculate score based on all accumulated data
        score, reasoning, breakdown = self.scorer.calculate_score(
            extracted,  # All data collected so far (current + previous)
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
            "extracted_data": extracted,  # Use the merged extracted data
            "lead_score": score,
            "lead_category": route,
            "suggested_agent": suggested_agent,
            "score_history": score_history,
            "analysis_metadata": analysis,
            "score_reasoning": reasoning
        }


# Create node for LangGraph workflow
async def intelligence_node(state: MinimalState) -> Dict[str, Any]:
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