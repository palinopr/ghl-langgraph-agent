"""
Natural Message Patterns - Templates for human-like conversations
Implements varied responses to avoid robotic patterns
"""
from typing import Dict, List, Optional, Any
import random


class NaturalMessageTemplates:
    """
    Provides natural message variations for each conversation stage
    Avoids robotic repetition by offering multiple options
    """
    
    # Maria's templates - Warm and helpful
    MARIA_TEMPLATES = {
        "greeting": {
            "es": [
                "¡Hola! 👋 Soy Maria de Main Outlet. Ayudo a negocios como el tuyo a nunca perder un cliente por WhatsApp. ¿Cómo te llamas?",
                "Hola hola 😊 Aquí Maria de Main Outlet. Me especializo en automatizar WhatsApp para que no pierdas ventas. ¿Cuál es tu nombre?",
                "¡Buenas! Soy Maria 👋 Ayudo a empresas a responder todos sus WhatsApp automáticamente. ¿Con quién tengo el gusto?",
                "¡Hey! Maria de Main Outlet aquí. ¿Sabías que puedes responder todos tus mensajes automáticamente? ¿Cómo te llamas?",
                "Hola 😊 Soy Maria y ayudo a negocios a captar más clientes por WhatsApp. ¿Tu nombre es...?",
            ],
            "en": [
                "Hi there! 👋 I'm Maria from Main Outlet. I help businesses like yours never miss a customer on WhatsApp. What's your name?",
                "Hello! 😊 Maria here from Main Outlet. I specialize in WhatsApp automation so you never lose sales. May I have your name?",
                "Hey! I'm Maria 👋 I help businesses respond to all their WhatsApp messages automatically. Who am I speaking with?",
                "Hi! Maria from Main Outlet here. Did you know you can respond to all messages automatically? What's your name?",
                "Hello 😊 I'm Maria and I help businesses capture more customers through WhatsApp. And your name is...?",
            ]
        },
        "ask_business": {
            "es": [
                "{greeting} {name}. ¿A qué te dedicas?",
                "{greeting} {name}, cuéntame, ¿qué tipo de negocio tienes?",
                "{name}, qué gusto conocerte. ¿En qué industria estás?",
                "Encantada, {name}. Dime, ¿cuál es tu negocio?",
                "{greeting} {name} 😊 ¿Qué tipo de empresa manejas?",
            ],
            "en": [
                "{greeting} {name}. What do you do?",
                "{greeting} {name}, tell me, what type of business do you have?",
                "{name}, great to meet you. What industry are you in?",
                "Nice to meet you, {name}. So, what's your business?",
                "{greeting} {name} 😊 What kind of company do you run?",
            ]
        },
        "ask_challenge": {
            "es": [
                "Ah, {ack} {business}. ¿Cuál es tu mayor reto con los mensajes de WhatsApp?",
                "{business}, {ack}. Dime, ¿qué es lo más difícil de manejar en WhatsApp?",
                "Ya veo, {business}. ¿Qué te quita más tiempo con los mensajes de clientes?",
                "{ack}, conozco bien ese sector. ¿Cuál es tu principal desafío con las conversaciones?",
                "Un {business}, qué bien. ¿Qué problema tienes con los mensajes?",
            ],
            "en": [
                "Ah, {ack} {business}. What's your biggest challenge with WhatsApp messages?",
                "{business}, {ack}. Tell me, what's the hardest part about managing WhatsApp?",
                "I see, {business}. What takes most of your time with customer messages?",
                "{ack}, I know that sector well. What's your main challenge with conversations?",
                "A {business}, great. What problem do you have with messages?",
            ]
        },
        "present_budget": {
            "es": [
                "Entiendo perfectamente. Puedo ayudarte con eso. Las soluciones empiezan en $300/mes. ¿Te funciona ese presupuesto?",
                "Definitivamente puedo ayudarte. Mis servicios van desde $300 al mes. ¿Está dentro de tu presupuesto?",
                "Me encanta, justo en eso me especializo. La inversión empieza en $300 mensuales. ¿Te parece bien?",
                "Perfecto, tengo la solución ideal. Los planes inician en $300/mes. ¿Trabajamos juntos?",
                "Claro que sí, puedo automatizar todo eso. Desde $300 al mes. ¿Comenzamos?",
            ],
            "en": [
                "I understand perfectly. I can help you with that. Solutions start at $300/month. Does that budget work for you?",
                "I can definitely help you. My services start from $300 per month. Is that within your budget?",
                "I love it, that's exactly what I specialize in. Investment starts at $300 monthly. Sound good?",
                "Perfect, I have the ideal solution. Plans start at $300/month. Shall we work together?",
                "Of course, I can automate all of that. From $300 per month. Shall we start?",
            ]
        }
    }
    
    # Carlos's templates - Professional and engaging
    CARLOS_TEMPLATES = {
        "greeting": {
            "es": [
                "¡{name}! Qué gusto. Soy Carlos, especialista en automatización. Veo que ya hablaste con Maria sobre {business}...",
                "Hola {name}, soy Carlos. Me comentó Maria que tienes un {business}. Fascinante sector...",
                "{name}, un placer. Carlos aquí. Entiendo que buscas automatizar tu {business}...",
                "¡Qué tal, {name}! Soy Carlos. Me encanta trabajar con {business}s. Cuéntame más...",
                "Saludos {name}, Carlos al habla. Los {business}s son mi especialidad. Platiquemos...",
            ],
            "en": [
                "{name}! Great to meet you. I'm Carlos, automation specialist. I see you spoke with Maria about {business}...",
                "Hi {name}, I'm Carlos. Maria told me you have a {business}. Fascinating sector...",
                "{name}, a pleasure. Carlos here. I understand you want to automate your {business}...",
                "Hey {name}! I'm Carlos. I love working with {business}s. Tell me more...",
                "Greetings {name}, Carlos speaking. {business}s are my specialty. Let's chat...",
            ]
        },
        "explore_goals": {
            "es": [
                "Me encanta tu visión. Ahora, ¿cuál es tu meta principal con la automatización?",
                "Excelente. Dime, ¿qué resultado específico buscas lograr?",
                "Muy bien. ¿Cuál sería tu objetivo ideal con WhatsApp?",
                "Perfecto. ¿Qué es lo más importante que quieres conseguir?",
                "Genial. ¿Cómo visualizas tu negocio con la automatización funcionando?",
            ],
            "en": [
                "I love your vision. Now, what's your main goal with automation?",
                "Excellent. Tell me, what specific result are you looking to achieve?",
                "Very good. What would be your ideal objective with WhatsApp?",
                "Perfect. What's the most important thing you want to accomplish?",
                "Great. How do you envision your business with automation working?",
            ]
        }
    }
    
    # Sofia's templates - Efficient and closing-focused
    SOFIA_TEMPLATES = {
        "greeting": {
            "es": [
                "{name}, ¡qué emoción! Soy Sofia y voy a ayudarte a implementar todo. ¿Listo para transformar tu {business}?",
                "¡{name}! Sofia aquí. Me encanta que estés listo para automatizar. ¿Empezamos con tu {business}?",
                "Hola {name}, soy Sofia. ¡Vamos a revolucionar tu {business}! ¿Preparado?",
                "{name}, qué gusto. Sofia al habla. Tu {business} va a despegar. ¿Comenzamos?",
                "¡Excelente decisión, {name}! Soy Sofia. Tu {business} está a punto de cambiar. ¿Listo?",
            ],
            "en": [
                "{name}, how exciting! I'm Sofia and I'll help you implement everything. Ready to transform your {business}?",
                "{name}! Sofia here. I love that you're ready to automate. Shall we start with your {business}?",
                "Hi {name}, I'm Sofia. Let's revolutionize your {business}! Ready?",
                "{name}, great to meet you. Sofia speaking. Your {business} is about to take off. Shall we begin?",
                "Excellent decision, {name}! I'm Sofia. Your {business} is about to change. Ready?",
            ]
        },
        "offer_appointment": {
            "es": [
                "¡Perfecto! Tengo estos horarios disponibles para nuestra llamada:\n\n{slots}\n\n¿Cuál prefieres?",
                "¡Genial! Mira, puedo atenderte en estos horarios:\n\n{slots}\n\n¿Qué te funciona mejor?",
                "¡Excelente! Aquí están mis próximos espacios:\n\n{slots}\n\n¿Cuál te acomoda?",
                "¡Me encanta tu decisión! Estos son los horarios:\n\n{slots}\n\n¿Cuál eliges?",
                "¡Súper! Tengo disponibilidad en:\n\n{slots}\n\n¿Qué horario te va mejor?",
            ],
            "en": [
                "Perfect! I have these times available for our call:\n\n{slots}\n\nWhich do you prefer?",
                "Great! Look, I can meet at these times:\n\n{slots}\n\nWhat works best for you?",
                "Excellent! Here are my next available slots:\n\n{slots}\n\nWhich suits you?",
                "I love your decision! These are the times:\n\n{slots}\n\nWhich do you choose?",
                "Super! I have availability at:\n\n{slots}\n\nWhat time works better for you?",
            ]
        }
    }
    
    # Natural acknowledgments
    ACKNOWLEDGMENTS = {
        "es": ["Ya veo", "Entiendo", "Claro", "Perfecto", "Genial", "Ok", "Me parece bien"],
        "en": ["I see", "Got it", "Sure", "Perfect", "Great", "Ok", "Sounds good"]
    }
    
    # Natural greetings for name response
    GREETINGS = {
        "es": ["Mucho gusto", "Un placer", "Encantada", "Qué tal", "Hola"],
        "en": ["Nice to meet you", "Pleasure to meet you", "Great to meet you", "Hello", "Hi"]
    }
    
    @classmethod
    def get_natural_response(
        cls,
        agent: str,
        stage: str,
        language: str = "es",
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get a natural response for the given stage"""
        data = data or {}
        
        # Get agent templates
        if agent == "maria":
            templates = cls.MARIA_TEMPLATES
        elif agent == "carlos":
            templates = cls.CARLOS_TEMPLATES
        elif agent == "sofia":
            templates = cls.SOFIA_TEMPLATES
        else:
            return ""
        
        # Get stage templates
        if stage not in templates:
            return ""
        
        # Select random template
        template = random.choice(templates[stage][language])
        
        # Fill in variables
        if "{greeting}" in template:
            template = template.replace("{greeting}", random.choice(cls.GREETINGS[language]))
        
        if "{ack}" in template:
            template = template.replace("{ack}", random.choice(cls.ACKNOWLEDGMENTS[language]))
        
        if "{name}" in template and data.get("name"):
            template = template.replace("{name}", data["name"])
        
        if "{business}" in template and data.get("business"):
            template = template.replace("{business}", data["business"])
        
        if "{slots}" in template and data.get("slots"):
            template = template.replace("{slots}", data["slots"])
        
        return template
    
    @classmethod
    def get_thinking_pause(cls, language: str = "es") -> str:
        """Get a natural thinking pause"""
        pauses = {
            "es": ["Déjame ver...", "A ver...", "Mmm...", "Bueno...", "Mira..."],
            "en": ["Let me see...", "Hmm...", "Well...", "So...", "Actually..."]
        }
        return random.choice(pauses[language])
    
    @classmethod
    def add_natural_typos(cls, message: str, frequency: float = 0.02) -> str:
        """Add natural typos and corrections"""
        if random.random() > frequency:
            return message
        
        words = message.split()
        if len(words) < 4:
            return message
        
        # Pick a random word to typo
        idx = random.randint(1, len(words) - 2)
        word = words[idx]
        
        if len(word) > 3:
            # Common typo patterns
            typo_patterns = [
                lambda w: w[:-1] + w[-1] * 2,  # Double last letter
                lambda w: w[0] + w[2] + w[1] + w[3:],  # Swap letters
                lambda w: w[:-1],  # Missing last letter
            ]
            
            typo_func = random.choice(typo_patterns)
            typo = typo_func(word)
            
            # Return with correction
            words[idx] = typo
            typo_message = " ".join(words)
            return f"{typo_message}\n{word}*"
        
        return message