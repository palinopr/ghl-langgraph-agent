"""
Data validation utilities for agent responses
Based on old agent rules from gohighlevel-messaging-agent
"""
from typing import Optional, Dict, Any
from app.utils.simple_logger import get_logger

logger = get_logger("data_validation")


def validate_response(field: str, response: str) -> bool:
    """
    Validate that response actually answers the question asked
    Based on sequence-enforcer.js validation rules
    
    Args:
        field: The field being collected (name, business, goal, budget, email)
        response: The user's response
        
    Returns:
        bool: True if response is valid for the field
    """
    if not response:
        return False
        
    lower_response = response.lower().strip()
    
    # Common non-answers to reject
    non_answers = ['sí', 'si', 'no', 'ok', 'vale', 'yes', 'okay', 'sure', 'claro']
    
    if field == 'name':
        # Should contain actual name, not yes/no
        if lower_response in non_answers:
            return False
        # Name should be at least 2 characters
        if len(lower_response) < 2:
            return False
        # Should not be just numbers
        if lower_response.isdigit():
            return False
        return True
    
    elif field == 'business' or field == 'business_type':
        # Should describe a business type
        if lower_response in non_answers:
            return False
        # Business description should be at least 3 characters
        if len(lower_response) < 3:
            return False
        return True
    
    elif field == 'goal' or field == 'problem':
        # Should describe a problem/challenge
        if len(lower_response) < 10:
            return False
        # Should not be just a yes/no answer
        if lower_response in non_answers:
            return False
        return True
    
    elif field == 'budget':
        # Should confirm budget or mention amount
        budget_indicators = [
            'sí', 'si', 'yes', 'claro', 'por supuesto', 'ok', 'dale', 
            'está bien', 'funciona', 'works', 'perfect', 'perfecto',
            '$', 'dollar', 'dolar', 'month', 'mes', 'mensual', 'monthly'
        ]
        # Check for numbers (budget amounts)
        if any(char.isdigit() for char in lower_response):
            return True
        # Check for budget confirmation words
        if any(indicator in lower_response for indicator in budget_indicators):
            return True
        return False
    
    elif field == 'email':
        # Should contain @ symbol
        if '@' not in response:
            return False
        # Basic email validation
        parts = response.split('@')
        if len(parts) != 2:
            return False
        if len(parts[0]) < 1 or len(parts[1]) < 3:
            return False
        if '.' not in parts[1]:
            return False
        return True
    
    else:
        logger.warning(f"Unknown field for validation: {field}")
        return False


def extract_valid_data(response: str, field: str) -> Optional[str]:
    """
    Extract and clean valid data from response
    
    Args:
        response: User's response
        field: The field being collected
        
    Returns:
        Cleaned data if valid, None otherwise
    """
    if not validate_response(field, response):
        return None
    
    # Clean and return the response
    cleaned = response.strip()
    
    if field == 'email':
        # Lowercase emails
        cleaned = cleaned.lower()
    elif field == 'name':
        # Capitalize names
        words = cleaned.split()
        cleaned = ' '.join(word.capitalize() for word in words)
    
    return cleaned


def check_data_completeness(state: Dict[str, Any]) -> Dict[str, bool]:
    """
    Check which required fields are complete in the state
    
    Args:
        state: Current conversation state
        
    Returns:
        Dict with field names as keys and completion status as values
    """
    completeness = {
        'name': False,
        'business_type': False,
        'goal': False,
        'budget': False,
        'email': False
    }
    
    # Check contact name
    if state.get('contact_name') and state['contact_name'] not in ['there', 'unknown', '']:
        completeness['name'] = True
    
    # Check business type
    if state.get('business_type') and state['business_type'] not in ['unknown', '']:
        completeness['business_type'] = True
    
    # Check goal/problem
    if state.get('business_goals') and len(state['business_goals']) > 10:
        completeness['goal'] = True
    
    # Check budget
    if state.get('budget_range') and state['budget_range'] not in ['unknown', '']:
        completeness['budget'] = True
    
    # Check email
    if state.get('contact_email') and '@' in state.get('contact_email', ''):
        completeness['email'] = True
    
    return completeness


def get_next_required_field(state: Dict[str, Any], agent_type: str) -> Optional[str]:
    """
    Get the next field to collect based on sequence rules
    
    Args:
        state: Current conversation state
        agent_type: Type of agent (maria, carlos, sofia)
        
    Returns:
        Next field to collect, or None if all complete
    """
    # Define the sequence for each agent
    sequence = ['name', 'business_type', 'goal', 'budget', 'email']
    
    completeness = check_data_completeness(state)
    
    # Find the first incomplete field in sequence
    for field in sequence:
        if not completeness[field]:
            logger.info(f"Next required field for {agent_type}: {field}")
            return field
    
    logger.info(f"All required fields complete for {agent_type}")
    return None


def validate_budget_confirmation(response: str, previous_score: int = 0) -> bool:
    """
    Special validation for budget confirmation
    Checks if response confirms $300+ budget
    
    Args:
        response: User's response
        previous_score: Previous lead score
        
    Returns:
        True if budget is confirmed
    """
    lower_response = response.lower()
    
    # Direct confirmations
    confirmations = [
        'sí', 'si', 'yes', 'claro', 'por supuesto', 
        'ok', 'dale', 'está bien', 'funciona', 'works',
        'perfect', 'perfecto', 'sure', 'of course',
        'absolutamente', 'absolutely', 'definitely'
    ]
    
    # Check for direct confirmation
    if any(confirm in lower_response for confirm in confirmations):
        return True
    
    # Check for amount mentions
    if '$' in response or 'dollar' in lower_response or 'dolar' in lower_response:
        # Extract numbers
        import re
        numbers = re.findall(r'\d+', response)
        for num in numbers:
            if int(num) >= 300:
                return True
    
    # Check for specific budget ranges
    budget_ranges = ['300', '500', '1000', 'mil', 'thousand']
    if any(amount in lower_response for amount in budget_ranges):
        return True
    
    return False