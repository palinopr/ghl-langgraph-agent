"""
Simple Intelligence Analyzer - LLM-based extraction
Replaces 852 lines of regex with a single well-crafted prompt
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from app.state.minimal_state import MinimalState
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
import json

logger = get_logger("simple_analyzer")


class SimpleLLMAnalyzer:
    """Extract information using LLM instead of regex patterns"""
    
    def __init__(self):
        self.model = create_openai_model(temperature=0.1)  # Low temp for consistency
        
    async def extract_from_message(self, 
                                  message: str, 
                                  previous_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract structured data from message using LLM
        
        Args:
            message: Current message to analyze
            previous_data: Previously extracted data
            
        Returns:
            Extracted information
        """
        previous_data = previous_data or {}
        
        # Craft a precise prompt for extraction
        system_prompt = """You are an information extraction assistant for a Spanish-speaking WhatsApp business automation service.
        
Extract the following information from the customer's message:
1. name - Customer's name (if they introduce themselves)
2. business_type - Type of business they have (be specific: restaurante, tienda, salon, etc.)
3. budget - Budget mentioned (keep original format, e.g., "300", "400+", "300-500")
4. preferred_contact_time - When they prefer to be contacted
5. pain_points - Business problems or needs they mention

IMPORTANT RULES:
- Extract ONLY from the current message, not from conversation history
- For business_type, use specific terms (restaurante, salon, clinica, etc.), NOT generic terms like "negocio" or "empresa"
- Understand variations and typos (e.g., "reaturante" → "restaurante", "tengo un gym" → "gym")
- If information is not present in the message, use null
- Return ONLY valid JSON

Examples:
Message: "Hola soy Juan y tengo un restaurante"
Output: {"name": "Juan", "business_type": "restaurante", "budget": null, "preferred_contact_time": null, "pain_points": null}

Message: "mi presupuesto es como unos 300 al mes"
Output: {"name": null, "business_type": null, "budget": "300", "preferred_contact_time": null, "pain_points": null}

Message: "tengo un reaturante y estoy perdiendo clientes"
Output: {"name": null, "business_type": "restaurante", "budget": null, "preferred_contact_time": null, "pain_points": "perdiendo clientes"}

Message: "si claro"
Output: {"name": null, "business_type": null, "budget": null, "preferred_contact_time": null, "pain_points": null}"""

        user_prompt = f"Extract information from this message: \"{message}\""
        
        try:
            # Call LLM
            response = await self.model.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Handle None response
            if not response or not response.content:
                logger.error("LLM returned no content")
                return previous_data
            
            # Log the response for debugging
            logger.debug(f"LLM response: {response.content}")
            
            # Parse JSON response
            extracted = json.loads(response.content)
            
            # Merge with previous data (only override if new data exists)
            result = {
                "name": extracted.get("name") or previous_data.get("name"),
                "business_type": extracted.get("business_type") or previous_data.get("business_type"),
                "budget": extracted.get("budget") or previous_data.get("budget"),
                "goal": extracted.get("pain_points") or previous_data.get("goal"),
                "email": previous_data.get("email"),  # Email not extracted by LLM
                "phone": previous_data.get("phone"),  # Phone not extracted by LLM
                "preferred_contact_time": extracted.get("preferred_contact_time") or previous_data.get("preferred_contact_time")
            }
            
            logger.info(f"LLM extraction successful: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return previous_data
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return previous_data


class SimpleLeadScorer:
    """Same scoring logic but cleaner"""
    
    def calculate_score(self, 
                       extracted_data: Dict[str, Any], 
                       previous_score: int = 0,
                       conversation_length: int = 0) -> Tuple[int, str, Dict[str, int]]:
        """Calculate lead score (1-10) based on extracted data"""
        
        score_breakdown = {
            "base": 1,
            "name": 0,
            "business": 0,
            "goal": 0,
            "budget": 0,
            "engagement": 0
        }
        
        reasoning_parts = []
        
        # Name: 1 point
        if extracted_data.get("name"):
            score_breakdown["name"] = 1
            reasoning_parts.append("has name")
        
        # Business: 2 points
        if extracted_data.get("business_type"):
            score_breakdown["business"] = 2
            reasoning_parts.append(f"has business ({extracted_data['business_type']})")
        
        # Goal/Problem: 1 point
        if extracted_data.get("goal"):
            score_breakdown["goal"] = 1
            reasoning_parts.append("has goal/problem")
        
        # Budget: 3 points for confirmed budget
        if extracted_data.get("budget"):
            budget_str = str(extracted_data["budget"])
            # Substantial budget check
            if any(x in budget_str for x in ["300", "400", "500"]) or \
               len(budget_str) >= 3 and budget_str.isdigit():
                score_breakdown["budget"] = 3
                reasoning_parts.append(f"substantial budget ({budget_str})")
            else:
                score_breakdown["budget"] = 1
                reasoning_parts.append(f"budget mentioned ({budget_str})")
        
        # Engagement bonus for long conversations
        if conversation_length > 10:
            score_breakdown["engagement"] = 1
            reasoning_parts.append("highly engaged")
        
        # Calculate total
        total_score = sum(score_breakdown.values())
        
        # Never decrease score
        final_score = max(total_score, previous_score)
        
        if final_score > total_score:
            reasoning_parts.append(f"maintained previous score ({previous_score})")
        
        # Cap at 10
        final_score = min(10, final_score)
        
        reasoning = f"Score {final_score}: " + ", ".join(reasoning_parts) if reasoning_parts else "minimal information"
        
        return final_score, reasoning, score_breakdown


class SimpleIntelligenceAnalyzer:
    """Main analyzer using LLM for extraction"""
    
    def __init__(self):
        self.extractor = SimpleLLMAnalyzer()
        self.scorer = SimpleLeadScorer()
        
    async def analyze(self, state: MinimalState) -> Dict[str, Any]:
        """Analyze conversation and extract intelligence using LLM"""
        
        # Get conversation context
        messages = state.get("messages", [])
        if not messages:
            return state
            
        current_message = messages[-1].content if messages else ""
        
        # Get previous data
        previous_score = state.get("lead_score", 0)
        previous_data = state.get("extracted_data", {})
        
        # Extract using LLM
        extracted = await self.extractor.extract_from_message(current_message, previous_data)
        
        # Calculate score
        score, reasoning, breakdown = self.scorer.calculate_score(
            extracted,
            previous_score,
            len(messages)
        )
        
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
            "extraction_method": "llm_based",
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
            "extracted_data": extracted,
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
    analyzer = SimpleIntelligenceAnalyzer()
    
    try:
        enriched_state = await analyzer.analyze(state)
        
        logger.info(
            f"Intelligence analysis complete: Score {enriched_state['lead_score']}, "
            f"Route: {enriched_state['lead_category']}, "
            f"Suggested: {enriched_state['suggested_agent']}"
        )
        
        return enriched_state
        
    except Exception as e:
        logger.error(f"Intelligence analysis failed: {str(e)}", exc_info=True)
        return state


__all__ = [
    "SimpleIntelligenceAnalyzer",
    "SimpleLLMAnalyzer",
    "SimpleLeadScorer",
    "intelligence_node"
]