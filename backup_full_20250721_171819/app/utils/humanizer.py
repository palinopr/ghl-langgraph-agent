"""
Conversation Humanizer - Makes agents sound more natural and less robotic
Based on LangGraph best practices for conversational AI
"""
from typing import Dict, List, Optional, Tuple, Any
import random
import re
import time
from app.utils.simple_logger import get_logger

logger = get_logger("humanizer")


class ConversationHumanizer:
    """
    Makes conversation responses more human-like
    - Adds natural variations
    - Includes typing indicators
    - Adds personality traits
    - Uses conversational patterns
    """
    
    # Typing speed variations (chars per second)
    TYPING_SPEEDS = {
        "slow": 10,    # Thoughtful typing
        "normal": 20,  # Average typing
        "fast": 30,    # Excited/urgent typing
    }
    
    # Natural conversation starters
    GREETINGS = {
        "es": [
            "¡Hola! 👋",
            "¡Hola! 😊", 
            "¡Buenas!",
            "Hola hola 👋",
            "¡Hey! 👋",
        ],
        "en": [
            "Hi there! 👋",
            "Hello! 😊",
            "Hey! 👋", 
            "Hi! How's it going?",
            "Hello there!",
        ]
    }
    
    # Natural transitions
    TRANSITIONS = {
        "es": {
            "acknowledgment": [
                "Ya veo",
                "Entiendo", 
                "Ah ok",
                "Perfecto",
                "Genial",
                "Me parece bien",
                "Claro"
            ],
            "thinking": [
                "Déjame ver...",
                "A ver...",
                "Mmm...",
                "Bueno...",
                "Mira...",
            ],
            "enthusiasm": [
                "¡Qué bueno!",
                "¡Excelente!",
                "¡Me encanta!",
                "¡Súper!",
                "¡Genial!"
            ]
        },
        "en": {
            "acknowledgment": [
                "I see",
                "Got it",
                "Understood", 
                "Perfect",
                "Great",
                "Sounds good",
                "Alright"
            ],
            "thinking": [
                "Let me see...",
                "Hmm...",
                "Well...",
                "So...",
                "Actually...",
            ],
            "enthusiasm": [
                "That's great!",
                "Excellent!",
                "Love it!",
                "Awesome!",
                "Perfect!"
            ]
        }
    }
    
    # Question variations for each stage
    QUESTION_VARIATIONS = {
        "name": {
            "es": [
                "¿Cuál es tu nombre?",
                "¿Cómo te llamas?",
                "¿Con quién tengo el gusto?",
                "¿Tu nombre es...?",
                "Antes de continuar, ¿cuál es tu nombre?",
            ],
            "en": [
                "What's your name?",
                "May I have your name?",
                "Who am I speaking with?",
                "And your name is...?",
                "Before we continue, what's your name?",
            ]
        },
        "business": {
            "es": [
                "¿Qué tipo de negocio tienes?",
                "¿A qué te dedicas?",
                "¿En qué industria estás?",
                "¿Cuál es tu negocio?",
                "Cuéntame, ¿qué tipo de empresa manejas?",
            ],
            "en": [
                "What type of business do you have?",
                "What industry are you in?",
                "What's your business?",
                "Tell me about your business",
                "What kind of company do you run?",
            ]
        },
        "challenge": {
            "es": [
                "¿Cuál es tu mayor desafío con los mensajes de WhatsApp?",
                "¿Qué es lo más difícil de manejar en WhatsApp?",
                "¿Qué problema tienes con los mensajes de clientes?",
                "¿Qué te quita más tiempo en WhatsApp?",
                "¿Cuál es tu principal reto con las conversaciones?",
            ],
            "en": [
                "What's your biggest challenge with WhatsApp messages?",
                "What's the hardest part about managing WhatsApp?",
                "What problem do you have with customer messages?",
                "What takes most of your time on WhatsApp?",
                "What's your main challenge with conversations?",
            ]
        }
    }
    
    # Personality traits for each agent
    AGENT_PERSONALITIES = {
        "maria": {
            "traits": ["helpful", "warm", "patient"],
            "emoji_frequency": 0.3,  # 30% chance of emoji
            "thinking_frequency": 0.4,  # 40% chance of thinking pause
            "enthusiasm_level": "medium"
        },
        "carlos": {
            "traits": ["professional", "knowledgeable", "engaging"],
            "emoji_frequency": 0.2,  # 20% chance
            "thinking_frequency": 0.5,  # 50% chance
            "enthusiasm_level": "high"
        },
        "sofia": {
            "traits": ["efficient", "friendly", "decisive"],
            "emoji_frequency": 0.25,  # 25% chance
            "thinking_frequency": 0.3,  # 30% chance
            "enthusiasm_level": "high"
        }
    }
    
    @classmethod
    def humanize_response(
        cls,
        response: str,
        agent_name: str,
        language: str = "es",
        conversation_stage: Optional[str] = None,
        is_excited: bool = False
    ) -> Tuple[str, float]:
        """
        Humanize a response and return typing duration
        
        Returns:
            Tuple of (humanized_response, typing_duration_seconds)
        """
        personality = cls.AGENT_PERSONALITIES.get(agent_name, {})
        
        # Add natural variations
        response = cls._add_variations(response, language, conversation_stage)
        
        # Add personality touches
        response = cls._add_personality(response, personality, language, is_excited)
        
        # Calculate typing duration
        typing_speed = "fast" if is_excited else "normal"
        if personality.get("thinking_frequency", 0) > random.random():
            typing_speed = "slow"
        
        duration = len(response) / cls.TYPING_SPEEDS[typing_speed]
        
        # Add natural pauses
        duration += random.uniform(0.5, 1.5)  # Thinking time
        
        return response, duration
    
    @classmethod
    def _add_variations(cls, response: str, language: str, stage: Optional[str]) -> str:
        """Add natural variations to responses"""
        # Don't modify if it's a tool instruction
        if response.startswith("USE_") or response.startswith("ESCALATE:"):
            return response
        
        # Add acknowledgment before response sometimes
        if random.random() < 0.3 and stage not in ["greeting", "waiting_for_name"]:
            ack = random.choice(cls.TRANSITIONS[language]["acknowledgment"])
            response = f"{ack}, {response.lower()}"
        
        # Add thinking indicator sometimes
        if random.random() < 0.2:
            thinking = random.choice(cls.TRANSITIONS[language]["thinking"])
            response = f"{thinking} {response}"
        
        # Replace rigid patterns with variations
        if stage in cls.QUESTION_VARIATIONS:
            for question in cls.QUESTION_VARIATIONS[stage][language]:
                if any(pattern in response for pattern in cls.QUESTION_VARIATIONS[stage][language][:1]):
                    # Replace with a random variation
                    new_question = random.choice(cls.QUESTION_VARIATIONS[stage][language])
                    response = re.sub(
                        r'[¿?][^?]+\?',
                        new_question,
                        response,
                        count=1
                    )
                    break
        
        return response
    
    @classmethod
    def _add_personality(
        cls,
        response: str,
        personality: Dict,
        language: str,
        is_excited: bool
    ) -> str:
        """Add personality touches to response"""
        # Add emoji based on personality
        if personality.get("emoji_frequency", 0) > random.random():
            # Don't add if already has emoji
            if not re.search(r'[😊👋🎯💡✨🚀💪🤝]', response):
                if is_excited or personality.get("enthusiasm_level") == "high":
                    response += " 🎯"
                else:
                    response += " 😊"
        
        # Add enthusiasm for high-enthusiasm personalities
        if is_excited and personality.get("enthusiasm_level") == "high":
            if random.random() < 0.5:
                enthusiasm = random.choice(cls.TRANSITIONS[language]["enthusiasm"])
                response = f"{enthusiasm} {response}"
        
        # Natural corrections (like fixing typos)
        if random.random() < 0.05:  # 5% chance
            words = response.split()
            if len(words) > 3:
                # Simulate a typo and correction
                idx = random.randint(1, len(words) - 2)
                original = words[idx]
                if len(original) > 3:
                    # Create typo
                    typo = original[:-1] + original[-1:] * 2
                    words[idx] = typo
                    response = " ".join(words)
                    # Add correction
                    response += f"\n{original}*"
        
        return response
    
    @classmethod
    def get_typing_indicator_duration(cls, message_length: int, agent_name: str) -> float:
        """Get realistic typing indicator duration"""
        base_speed = cls.TYPING_SPEEDS["normal"]
        personality = cls.AGENT_PERSONALITIES.get(agent_name, {})
        
        # Adjust based on personality
        if "efficient" in personality.get("traits", []):
            base_speed = cls.TYPING_SPEEDS["fast"]
        elif "thoughtful" in personality.get("traits", []):
            base_speed = cls.TYPING_SPEEDS["slow"]
        
        # Calculate duration
        duration = message_length / base_speed
        
        # Add variability
        duration *= random.uniform(0.8, 1.2)
        
        # Add thinking pauses
        duration += random.uniform(0.3, 1.0)
        
        return min(duration, 5.0)  # Cap at 5 seconds
    
    @classmethod
    def should_add_typing_pause(cls, context: Dict[str, Any]) -> bool:
        """Determine if we should show typing indicator"""
        # Always show typing for longer messages
        if context.get("message_length", 0) > 50:
            return True
        
        # Show typing when switching topics
        if context.get("topic_change", False):
            return True
        
        # Random chance based on personality
        agent = context.get("agent_name", "maria")
        personality = cls.AGENT_PERSONALITIES.get(agent, {})
        return random.random() < personality.get("thinking_frequency", 0.3)
    
    @classmethod
    def make_response_natural(
        cls,
        template: str,
        collected_data: Dict[str, Any],
        language: str = "es",
        agent_name: str = "maria"
    ) -> str:
        """
        Transform template responses into natural variations
        """
        # Start with template
        response = template
        
        # Fill in data naturally
        if "{name}" in response and collected_data.get("name"):
            response = response.replace("{name}", collected_data["name"])
        
        if "{business}" in response and collected_data.get("business_type"):
            # Add natural acknowledgment
            business = collected_data["business_type"]
            if language == "es":
                if random.random() < 0.5:
                    business = f"un {business}" if not business.startswith("un") else business
            response = response.replace("{business}", business)
        
        if "{email}" in response and collected_data.get("email"):
            response = response.replace("{email}", collected_data["email"])
        
        # Make greeting more natural
        if "¡Hola! 👋" in response:
            greeting = random.choice(cls.GREETINGS[language])
            response = response.replace("¡Hola! 👋", greeting)
        
        # Vary "Mucho gusto"
        if "Mucho gusto," in response:
            variations = [
                "Mucho gusto,",
                "Un placer,",
                "Encantado,",
                "Qué tal",
                "Hola"
            ] if language == "es" else [
                "Nice to meet you,",
                "Pleasure to meet you,",
                "Great to meet you,",
                "Hello",
                "Hi"
            ]
            response = response.replace("Mucho gusto,", random.choice(variations))
        
        # Make questions sound more conversational
        response = cls._conversationalize_questions(response, language)
        
        return response
    
    @classmethod
    def _conversationalize_questions(cls, response: str, language: str) -> str:
        """Make questions sound more conversational"""
        if language == "es":
            # Add conversational prefixes sometimes
            if "¿" in response and random.random() < 0.3:
                prefixes = [
                    "Oye,",
                    "Dime,",
                    "Cuéntame,",
                    "Por cierto,",
                ]
                prefix = random.choice(prefixes)
                response = response.replace("¿", f"{prefix} ¿")
            
            # Make budget question softer
            if "$300" in response and "presupuesto" in response:
                if random.random() < 0.5:
                    response = response.replace(
                        "Mis soluciones empiezan en $300/mes",
                        "Las soluciones que ofrezco van desde $300 al mes"
                    )
        
        return response