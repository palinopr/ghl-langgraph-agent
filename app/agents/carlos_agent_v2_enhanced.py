"""
Carlos - Lead Qualification Agent (ENHANCED VERSION)
With parallel tool execution and better context management
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage
from langchain_core.messages.utils import trim_messages
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from langchain_core.tools import tool
from app.tools.agent_tools_v2 import qualification_tools_v2
from app.utils.simple_logger import get_logger
from app.config import get_settings
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = get_logger("carlos_v2_enhanced")


class CarlosState(AgentState):
    """Extended state for Carlos agent with parallel processing"""
    contact_id: str
    contact_name: Optional[str]
    business_type: Optional[str]
    business_goals: Optional[str]
    budget_range: Optional[str]
    qualification_score: int = 0
    qualification_status: Optional[str]
    # New fields for enhanced features
    parallel_checks_enabled: bool = True
    qualification_results: Dict[str, Any] = {}


# Parallel qualification tools
@tool
async def parallel_qualification_check(
    state: Annotated[CarlosState, InjectedState]
) -> Dict[str, Any]:
    """
    Perform multiple qualification checks in parallel for faster processing
    """
    contact_id = state.get("contact_id")
    
    async def check_business_viability():
        """Check if business type is suitable for our services"""
        business_type = state.get("business_type", "").lower()
        suitable_businesses = ["restaurant", "retail", "service", "ecommerce", "healthcare"]
        
        is_suitable = any(biz in business_type for biz in suitable_businesses)
        return {
            "check": "business_viability",
            "passed": is_suitable,
            "score": 3 if is_suitable else 0,
            "details": f"Business type '{business_type}' is {'suitable' if is_suitable else 'not ideal'}"
        }
    
    async def check_budget_qualification():
        """Verify budget meets minimum requirements"""
        budget = state.get("budget_range", "")
        
        # Extract numeric value from budget string
        import re
        numbers = re.findall(r'\d+', budget)
        budget_value = int(numbers[0]) if numbers else 0
        
        meets_minimum = budget_value >= 300
        return {
            "check": "budget_qualification", 
            "passed": meets_minimum,
            "score": 4 if meets_minimum else 2,
            "details": f"Budget ${budget_value} {'meets' if meets_minimum else 'below'} minimum"
        }
    
    async def check_readiness_signals():
        """Analyze conversation for buying readiness signals"""
        messages = state.get("messages", [])
        recent_messages = " ".join([m.content for m in messages[-5:] if hasattr(m, 'content')])
        
        readiness_keywords = ["ready", "start", "begin", "asap", "soon", "interested", "how much", "pricing"]
        urgency_keywords = ["urgent", "quickly", "fast", "immediately", "now"]
        
        readiness_score = sum(1 for keyword in readiness_keywords if keyword in recent_messages.lower())
        urgency_score = sum(2 for keyword in urgency_keywords if keyword in recent_messages.lower())
        
        total_signal_score = readiness_score + urgency_score
        
        return {
            "check": "readiness_signals",
            "passed": total_signal_score >= 2,
            "score": min(total_signal_score, 3),
            "details": f"Readiness level: {total_signal_score}/5"
        }
    
    # Run all checks in parallel
    try:
        results = await asyncio.gather(
            check_business_viability(),
            check_budget_qualification(),
            check_readiness_signals(),
            return_exceptions=True
        )
        
        # Process results
        total_score = 0
        all_checks = {}
        failed_checks = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Qualification check failed: {result}")
                continue
            
            all_checks[result["check"]] = result
            total_score += result.get("score", 0)
            
            if not result["passed"]:
                failed_checks.append(result["check"])
        
        # Determine qualification status
        if total_score >= 8:
            status = "highly_qualified"
            recommendation = "Transfer to Sofia immediately"
        elif total_score >= 5:
            status = "qualified"
            recommendation = "Continue qualification, then transfer to Sofia"
        else:
            status = "needs_nurturing"
            recommendation = "Continue building relationship"
        
        return {
            "total_score": total_score,
            "status": status,
            "recommendation": recommendation,
            "checks": all_checks,
            "failed_checks": failed_checks,
            "summary": f"Lead scored {total_score}/10. {recommendation}"
        }
        
    except Exception as e:
        logger.error(f"Parallel qualification check error: {e}")
        return {
            "error": str(e),
            "status": "check_failed",
            "recommendation": "Perform manual qualification"
        }


def carlos_prompt(state: CarlosState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Carlos with context window management
    """
    # Trim messages if needed
    messages = state.get("messages", [])
    if messages and len(messages) > 10:
        try:
            trimmed_messages = trim_messages(
                messages[1:],
                max_tokens=3000,
                strategy="last",
                allow_partial=True
            )
            messages = messages[:1] + trimmed_messages
            logger.info(f"Trimmed conversation to {len(messages)} messages")
        except Exception as e:
            logger.warning(f"Failed to trim messages: {e}")
    
    # Build context from state
    contact_name = state.get("contact_name", "there")
    qualification_score = state.get("qualification_score", 0)
    qualification_results = state.get("qualification_results", {})
    
    # Add qualification context
    context = ""
    if qualification_results:
        context = f"\nQualification Results: {qualification_results.get('summary', '')}"
    
    system_prompt = f"""You are Carlos, a lead qualification specialist for Main Outlet Media.

Your role is to:
1. Identify business needs and pain points
2. Qualify budget (minimum $300/month)
3. Assess urgency and readiness to buy
4. Gather key information efficiently
5. Use the parallel qualification tool when you have enough information

Current Lead Score: {qualification_score}/10
{context}

Important:
- Be friendly but professional
- Ask open-ended questions
- Listen actively and show empathy
- Use the parallel_qualification_check tool when appropriate
- Transfer qualified leads (score 5+) to Sofia

You're speaking with {contact_name}."""

    return [{"role": "system", "content": system_prompt}] + messages


# Enhanced tools list with parallel checker
enhanced_qualification_tools = qualification_tools_v2 + [parallel_qualification_check]


def create_carlos_agent():
    """Create Carlos agent with enhanced features"""
    settings = get_settings()
    
    agent = create_react_agent(
        model=f"openai:{getattr(settings, 'openai_model', 'gpt-4-turbo')}",
        tools=enhanced_qualification_tools,
        state_schema=CarlosState,
        prompt=carlos_prompt,
        name="carlos_enhanced"
    )
    
    return agent


async def carlos_node_v2_enhanced(state: CarlosState) -> Union[Dict[str, Any], Command]:
    """
    Enhanced Carlos node with parallel processing and error recovery
    """
    agent = create_carlos_agent()
    
    try:
        # Enable parallel checks by default
        state["parallel_checks_enabled"] = True
        
        # Process with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = await agent.ainvoke(state)
                
                # Check if qualification is complete
                if "qualification_results" in result:
                    score = result["qualification_results"].get("total_score", 0)
                    logger.info(f"Lead qualified with score: {score}")
                    
                    # Auto-transfer if highly qualified
                    if score >= 8:
                        return Command(
                            goto="sofia",
                            update={
                                "messages": result.get("messages", []),
                                "qualification_score": score,
                                "next_agent": "sofia"
                            }
                        )
                
                return result
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Attempt {retry_count} failed: {e}")
                
                if retry_count >= max_retries:
                    return {
                        "messages": [{
                            "role": "assistant",
                            "content": "I apologize for the technical difficulty. Let me gather your information another way. "
                                     "What's your main business challenge right now?"
                        }],
                        "error": str(e),
                        "parallel_checks_enabled": False  # Disable parallel checks on error
                    }
                
                await asyncio.sleep(2 ** retry_count)
                
    except Exception as e:
        logger.error(f"Critical error in Carlos node: {e}", exc_info=True)
        return {
            "messages": [{
                "role": "assistant",
                "content": "Let me connect you with another specialist who can help."
            }],
            "error": str(e),
            "next_agent": "maria",
            "should_continue": True
        }


# Quick qualification function
async def quick_qualify_lead(
    contact_id: str,
    business_type: str,
    budget: str,
    goals: str
) -> Dict[str, Any]:
    """
    Quickly qualify a lead with known information
    """
    state = CarlosState(
        contact_id=contact_id,
        business_type=business_type,
        budget_range=budget,
        business_goals=goals,
        messages=[{
            "role": "user",
            "content": f"I have a {business_type} and my budget is {budget}. I need help with {goals}."
        }]
    )
    
    # Run parallel qualification
    result = await parallel_qualification_check.ainvoke({}, state=state)
    return result


# Export enhanced components
carlos_node_v2 = carlos_node_v2_enhanced
__all__ = [
    "CarlosState",
    "create_carlos_agent",
    "carlos_node_v2",
    "parallel_qualification_check",
    "quick_qualify_lead"
]