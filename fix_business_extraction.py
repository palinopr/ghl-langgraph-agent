#!/usr/bin/env python3
"""
Fix business extraction in supervisor_brain_simple.py
Add more robust extraction and logging
"""

# The fix we need to apply to supervisor_brain_simple.py
fix_code = '''
# Enhanced business extraction with better logging
def extract_business_type(current_message: str, logger) -> Optional[str]:
    """Extract business type with detailed logging"""
    
    logger.info(f"🔍 Extracting business from: '{current_message}'")
    
    # Direct matches (highest priority)
    direct_business_words = [
        "restaurante", "restaurant", "tienda", "salon", "salón", 
        "barbería", "barberia", "clinica", "clínica", "consultorio",
        "agencia", "hotel", "gym", "gimnasio", "spa", "café", "cafe",
        "pizzería", "pizzeria", "panadería", "panaderia", "farmacia"
    ]
    
    message_lower = current_message.lower().strip()
    
    # Check direct matches
    for business in direct_business_words:
        if business in message_lower:
            logger.info(f"✅ Found business type: {business}")
            return business
    
    # Pattern matches
    business_patterns = [
        # "tengo un/una X"
        r'(?:tengo un|tengo una)\s+(\w+)',
        # "mi negocio es un/una X"  
        r'mi negocio es (?:un|una)\s+(\w+)',
        # "es un/una X"
        r'es (?:un|una)\s+(\w+)',
        # Just the business word alone (if it's the whole message)
        r'^(\w+)$'
    ]
    
    for pattern in business_patterns:
        match = re.search(pattern, message_lower)
        if match:
            potential_business = match.group(1)
            logger.info(f"🔎 Pattern match found: {potential_business}")
            
            # Validate it's a known business type
            if any(biz in potential_business for biz in direct_business_words):
                logger.info(f"✅ Validated business type: {potential_business}")
                return potential_business
    
    # Check if answering "what type of business" question
    # This handles single-word responses after the question
    if len(message_lower.split()) <= 3:  # Short response
        # Could be a business type response
        cleaned = message_lower.strip().rstrip('.').rstrip('!').rstrip('?')
        if cleaned in direct_business_words:
            logger.info(f"✅ Single word business type: {cleaned}")
            return cleaned
    
    logger.info("❌ No business type found")
    return None

# In the supervisor_brain_simple_node function, replace the business extraction with:
extracted["business_type"] = extract_business_type(current_message, logger)
'''

print("🔧 FIX FOR BUSINESS EXTRACTION")
print("="*60)
print("\nThe current code has business extraction but it's not working properly.")
print("\nHere's what needs to be fixed in supervisor_brain_simple.py:")
print("\n1. Add more robust extraction logic")
print("2. Add detailed logging to debug issues")
print("3. Handle single-word responses like 'Restaurante'")
print("4. Handle various Spanish business types")
print("\nThe fix adds:")
print("- Direct word matching for common business types")
print("- Pattern matching for phrases")
print("- Single-word response handling")
print("- Extensive logging to debug issues")