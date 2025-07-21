"""
Pre-Model Hooks for LangGraph Agents
These hooks prepare context before LLM calls to prevent repetition
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from app.utils.conversation_analyzer import ConversationAnalyzer
from app.utils.simple_logger import get_logger
from app.utils.humanizer import ConversationHumanizer
from app.utils.natural_messages import NaturalMessageTemplates

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
    and adds human-like conversation patterns
    """
    # Get base context
    result = conversation_context_hook(state)
    
    # Get conversation analysis
    collected = result.get("collected_data", {})
    stage = result.get("current_stage", "greeting")
    language = "es"  # Default to Spanish
    
    # Check language from last message
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            content = last_msg.content.lower()
            if any(word in content for word in ["hello", "hi", "yes", "no", "what", "how"]):
                language = "en"
    
    # Add Maria-specific guidance with natural templates
    maria_guidance = f"""
🚨 MARIA - NATURAL CONVERSATION RULES:
1. Check the "INFORMATION ALREADY COLLECTED" section above
2. NEVER ask for information that's already been collected
3. If you see "✅ Business: restaurante", do NOT ask "¿Qué tipo de negocio tienes?"
4. Continue the conversation from where it left off
5. Use the information collected to personalize your responses

💡 NATURAL RESPONSE TEMPLATES:
Instead of robotic responses, use these natural variations:

{_get_natural_templates_for_stage("maria", stage, language, collected)}

🎯 PERSONALITY TRAITS:
- Be warm and helpful
- Use emojis sparingly (30% of messages)
- Add thinking pauses occasionally ("Déjame ver...", "A ver...")
- Vary your acknowledgments ("Ya veo", "Entiendo", "Claro")
- Sound genuinely interested in their business
"""
    
    # Add guidance to the context message
    if result["llm_input_messages"]:
        context_content = result["llm_input_messages"][0].content
        enhanced_content = context_content + "\n\n" + maria_guidance
        result["llm_input_messages"][0] = SystemMessage(content=enhanced_content)
    
    return result


def _get_natural_templates_for_stage(agent: str, stage: str, language: str, collected: Dict) -> str:
    """Get natural template examples for current stage"""
    # Map conversation stages to template stages
    stage_mapping = {
        "greeting": "greeting",
        "collecting_name": "greeting",
        "collecting_business": "ask_business",
        "collecting_challenge": "ask_challenge",
        "collecting_budget": "present_budget",
        "collecting_email": "ask_email",
        "offering_appointment": "offer_appointment"
    }
    
    template_stage = stage_mapping.get(stage, "greeting")
    
    # Get examples from NaturalMessageTemplates
    examples = []
    for i in range(3):  # Show 3 examples
        example = NaturalMessageTemplates.get_natural_response(
            agent=agent,
            stage=template_stage,
            language=language,
            data=collected
        )
        if example:
            examples.append(f"• {example}")
    
    if examples:
        return "Examples of natural responses:\n" + "\n".join(examples)
    else:
        return "Use natural, conversational language"


def carlos_context_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized hook for Carlos focusing on qualification
    with professional yet engaging conversation style
    """
    # Get base context
    result = conversation_context_hook(state)
    
    # Get conversation state
    collected = result.get("collected_data", {})
    stage = result.get("current_stage", "greeting")
    language = "es"
    
    # Check language
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            content = last_msg.content.lower()
            if any(word in content for word in ["hello", "hi", "yes", "no", "what", "how"]):
                language = "en"
    
    # Add Carlos-specific guidance
    carlos_guidance = f"""
🚨 CARLOS - QUALIFICATION FOCUS:
1. You're handling WARM leads (score 5-7)
2. Build on information already collected - don't repeat questions
3. Focus on understanding their specific needs and goals
4. If budget is already confirmed, move to scheduling discussion

💡 NATURAL CONVERSATION STYLE:
{_get_natural_templates_for_stage("carlos", stage, language, collected)}

🎯 PERSONALITY TRAITS:
- Professional but engaging
- Use industry knowledge to build credibility
- Add value with insights (not just questions)
- Show genuine interest with follow-up questions
- Use emojis sparingly (20% of messages)
- Add thinking pauses when providing insights
"""
    
    if result["llm_input_messages"]:
        context_content = result["llm_input_messages"][0].content
        enhanced_content = context_content + "\n\n" + carlos_guidance
        result["llm_input_messages"][0] = SystemMessage(content=enhanced_content)
    
    return result


def sofia_context_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized hook for Sofia focusing on closing
    with efficient yet friendly style
    """
    # Get base context
    result = conversation_context_hook(state)
    
    # Get conversation state
    collected = result.get("collected_data", {})
    stage = result.get("current_stage", "greeting")
    language = "es"
    
    # Check language
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            content = last_msg.content.lower()
            if any(word in content for word in ["hello", "hi", "yes", "no", "what", "how"]):
                language = "en"
    
    # Add Sofia-specific guidance
    sofia_guidance = f"""
🚨 SOFIA - CLOSING FOCUS:
1. You're handling HOT leads (score 8-10) ready to buy
2. All information should already be collected
3. Focus on scheduling the appointment
4. If customer mentions a time, use the appointment booking tool immediately

💡 NATURAL CLOSING STYLE:
{_get_natural_templates_for_stage("sofia", stage, language, collected)}

🎯 PERSONALITY TRAITS:
- Efficient but friendly
- Create urgency without being pushy
- Use excitement and enthusiasm ("¡Qué emoción!", "¡Excelente decisión!")
- Keep messages short and action-oriented
- Use emojis moderately (25% of messages)
- Be decisive and guide the conversation to booking
"""
    
    if result["llm_input_messages"]:
        context_content = result["llm_input_messages"][0].content
        enhanced_content = context_content + "\n\n" + sofia_guidance
        result["llm_input_messages"][0] = SystemMessage(content=enhanced_content)
    
    return result