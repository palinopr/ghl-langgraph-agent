"""
Pre-Model Hooks for LangGraph Agents
These hooks prepare context before LLM calls to prevent repetition
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from app.utils.conversation_analyzer import ConversationAnalyzer
from app.utils.simple_logger import get_logger

logger = get_logger("pre_model_hooks")


def conversation_context_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-model hook that analyzes conversation and provides context
    This prevents agents from repeating questions
    """
    messages = state.get("messages", [])
    
    # Analyze conversation to understand what's been collected
    analysis = ConversationAnalyzer.analyze_conversation(messages)
    
    # Build context message
    context_parts = []
    
    # What we've collected
    collected = analysis["collected_data"]
    if any(v for v in collected.values() if v):
        context_parts.append("📊 INFORMATION ALREADY COLLECTED:")
        if collected["name"]:
            context_parts.append(f"✅ Name: {collected['name']}")
        if collected["business_type"]:
            context_parts.append(f"✅ Business: {collected['business_type']}")
        if collected["challenge"]:
            context_parts.append(f"✅ Challenge: {collected['challenge']}")
        if collected["budget_confirmed"]:
            context_parts.append(f"✅ Budget: Confirmed ($300+)")
        if collected["email"]:
            context_parts.append(f"✅ Email: {collected['email']}")
    
    # What we've already asked
    if analysis["questions_asked"]:
        context_parts.append(f"\n❌ QUESTIONS ALREADY ASKED: {', '.join(analysis['questions_asked'])}")
        context_parts.append("⚠️ DO NOT ask these questions again!")
    
    # What we're expecting
    if analysis["expecting_answer_for"]:
        context_parts.append(f"\n⏳ EXPECTING: Answer for {analysis['expecting_answer_for']}")
        context_parts.append(f"💡 The last message is likely their {analysis['expecting_answer_for']}")
    
    # What to ask next
    if analysis["next_question_to_ask"]:
        context_parts.append(f"\n➡️ NEXT: Ask about {analysis['next_question_to_ask']}")
    
    # Language preference
    context_parts.append(f"\n🌐 Language: {'Spanish' if analysis['language'] == 'es' else 'English'}")
    
    # Create context message
    context_message = SystemMessage(content="\n".join(context_parts))
    
    # Trim messages to fit token limit
    trimmed_messages = trim_messages(
        messages,
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=2000,
        start_on="human",
        end_on=("human", "tool"),
    )
    
    # Add context at the beginning
    enhanced_messages = [context_message] + trimmed_messages
    
    # Update state with analysis results
    return {
        "llm_input_messages": enhanced_messages,
        "collected_data": collected,
        "questions_asked": list(analysis["questions_asked"]),
        "expecting_answer_for": analysis["expecting_answer_for"],
        "current_stage": analysis["current_stage"].value,
        "conversation_summary": analysis["conversation_summary"]
    }


def maria_context_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized hook for Maria that emphasizes not repeating questions
    """
    # Get base context
    result = conversation_context_hook(state)
    
    # Add Maria-specific guidance
    maria_guidance = """
🚨 MARIA - CRITICAL RULES:
1. Check the "INFORMATION ALREADY COLLECTED" section above
2. NEVER ask for information that's already been collected
3. If you see "✅ Business: restaurante", do NOT ask "¿Qué tipo de negocio tienes?"
4. Continue the conversation from where it left off
5. Use the information collected to personalize your responses
"""
    
    # Add guidance to the context message
    if result["llm_input_messages"]:
        context_content = result["llm_input_messages"][0].content
        enhanced_content = context_content + "\n\n" + maria_guidance
        result["llm_input_messages"][0] = SystemMessage(content=enhanced_content)
    
    return result


def carlos_context_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized hook for Carlos focusing on qualification
    """
    # Get base context
    result = conversation_context_hook(state)
    
    # Add Carlos-specific guidance
    carlos_guidance = """
🚨 CARLOS - QUALIFICATION FOCUS:
1. You're handling WARM leads (score 5-7)
2. Build on information already collected - don't repeat questions
3. Focus on understanding their specific needs and goals
4. If budget is already confirmed, move to scheduling discussion
"""
    
    if result["llm_input_messages"]:
        context_content = result["llm_input_messages"][0].content
        enhanced_content = context_content + "\n\n" + carlos_guidance
        result["llm_input_messages"][0] = SystemMessage(content=enhanced_content)
    
    return result


def sofia_context_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized hook for Sofia focusing on closing
    """
    # Get base context
    result = conversation_context_hook(state)
    
    # Add Sofia-specific guidance
    sofia_guidance = """
🚨 SOFIA - CLOSING FOCUS:
1. You're handling HOT leads (score 8-10) ready to buy
2. All information should already be collected
3. Focus on scheduling the appointment
4. If customer mentions a time, use the appointment booking tool immediately
"""
    
    if result["llm_input_messages"]:
        context_content = result["llm_input_messages"][0].content
        enhanced_content = context_content + "\n\n" + sofia_guidance
        result["llm_input_messages"][0] = SystemMessage(content=enhanced_content)
    
    return result