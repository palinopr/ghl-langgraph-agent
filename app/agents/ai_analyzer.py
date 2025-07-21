"""
AI-based analyzer that understands customer intent, not just patterns
"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from app.utils.model_factory import create_openai_model
from app.utils.simple_logger import get_logger
import json

logger = get_logger("ai_analyzer")


async def analyze_customer_intent(
    message: str, 
    conversation_history: list = None,
    previous_context: dict = None
) -> Dict[str, Any]:
    """
    Use AI to understand what the customer is actually trying to say
    Instead of pattern matching, we ask the AI to extract meaning
    """
    
    from langchain_openai import ChatOpenAI
    model = ChatOpenAI(model="gpt-4-turbo", temperature=0.0)
    
    # Build context from conversation
    context = ""
    if conversation_history and isinstance(conversation_history, list) and len(conversation_history) > 0:
        recent = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        context = "Recent conversation:\n"
        for msg in recent:
            if isinstance(msg, dict):
                role = "Customer" if msg.get("type") == "human" else "Assistant"
                context += f"{role}: {msg.get('content', '')}\n"
    
    if previous_context and isinstance(previous_context, dict):
        # Only include non-empty values
        relevant_context = {k: v for k, v in previous_context.items() if v}
        if relevant_context:
            context += f"\nKnown info: {json.dumps(relevant_context, ensure_ascii=False)}\n"
    
    prompt = f"""You are analyzing a customer message to extract business intelligence.
Focus on understanding WHAT they mean, not just what they say.

{context}

Current message: "{message}"

Extract the following (be generous in interpretation):
1. business_type: What kind of business do they have? (restaurant, store, clinic, etc)
   - "perdiendo restaurantes" → restaurant owner losing business
   - "mis tiendas" → store owner
   - "u. restaurante" → restaurant (u. = un)
   
2. intent: What do they want?
   - HELP_BUSINESS: Has business problems/needs help
   - INFO_GATHERING: Just asking questions
   - APPOINTMENT: Wants to schedule something
   - COMPLAINT: Expressing frustration
   
3. urgency: How urgent is their need?
   - HIGH: Using words like "perdiendo", "urgente", "problema"
   - MEDIUM: Interested but not desperate
   - LOW: Just exploring
   
4. sentiment: How are they feeling?
   - FRUSTRATED: Repeating issues, short messages
   - INTERESTED: Asking questions
   - URGENT: Expressing loss or problems
   
5. key_info: Extract any key details (name, email, budget, etc)

6. recommended_action: What should we do?
   - QUALIFY_BUSINESS: They have a business, get more info
   - OFFER_APPOINTMENT: They're ready to talk
   - ADDRESS_CONCERN: They have a specific problem
   - PROVIDE_INFO: They need information

Return as JSON.
"""
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Analyze this message: {message}")
    ]
    
    try:
        response = await model.ainvoke(messages)
        
        # Parse the response
        content = response.content if response else ""
        
        # Try to extract JSON from the response
        try:
            # First try direct JSON parsing
            result = json.loads(content)
        except:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except:
                    # Fallback parsing
                    result = {
                        "business_type": None,
                        "intent": "INFO_GATHERING",
                        "urgency": "LOW",
                        "sentiment": "NEUTRAL",
                        "key_info": {},
                        "recommended_action": "PROVIDE_INFO"
                    }
            else:
                # Fallback parsing
                result = {
                    "business_type": None,
                    "intent": "INFO_GATHERING",
                    "urgency": "LOW",
                    "sentiment": "NEUTRAL",
                    "key_info": {},
                    "recommended_action": "PROVIDE_INFO"
                }
        
        logger.info(f"AI Analysis: {json.dumps(result, ensure_ascii=False)}")
        return result
        
    except Exception as e:
        logger.error(f"AI analysis failed: {str(e)}", exc_info=True)
        # Return safe defaults
        return {
            "business_type": None,
            "intent": "INFO_GATHERING", 
            "urgency": "LOW",
            "sentiment": "NEUTRAL",
            "key_info": {},
            "recommended_action": "PROVIDE_INFO",
            "error": str(e)
        }


def calculate_smart_score(analysis: Dict[str, Any], current_score: int = 0) -> int:
    """
    Calculate score based on AI analysis, not pattern matching
    """
    score = max(current_score, 1)  # Start with at least 1
    
    # Business owner gets immediate boost
    if analysis.get("business_type"):
        score = max(score, 4)
        
        # Business + problem = qualified lead
        if analysis.get("intent") == "HELP_BUSINESS":
            score = max(score, 6)
            
        # Business + urgency = hot lead
        if analysis.get("urgency") == "HIGH":
            score = max(score, 7)
            
    # Ready for appointment = hottest lead
    if analysis.get("intent") == "APPOINTMENT":
        score = max(score, 8)
        
    # Has key info like budget
    key_info = analysis.get("key_info") or {}
    if isinstance(key_info, dict) and key_info.get("budget"):
        score = max(score, 7)
        
    return min(score, 10)  # Cap at 10


# Example usage:
if __name__ == "__main__":
    import asyncio
    
    test_cases = [
        "Estoy perdiendo restaurantes",
        "Tengo u. Restaurante y estoy perdiendo muchas reservas pq no puedo contestar todo",
        "Hola",
        "necesito ayuda urgente con mi negocio",
        "cuanto cuesta?",
        "quiero agendar una cita para mañana"
    ]
    
    async def test():
        for msg in test_cases:
            print(f"\nTesting: '{msg}'")
            result = await analyze_customer_intent(msg)
            score = calculate_smart_score(result)
            print(f"Intent: {result.get('intent')}")
            print(f"Business: {result.get('business_type')}")
            print(f"Urgency: {result.get('urgency')}")
            print(f"Score: {score}")
            print(f"Action: {result.get('recommended_action')}")
    
    asyncio.run(test())