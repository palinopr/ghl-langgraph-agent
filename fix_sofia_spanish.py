#!/usr/bin/env python3
"""
Fix Sofia to speak Spanish only
"""
import sys

def fix_sofia_spanish():
    """Update Sofia's prompt to Spanish only"""
    
    # Read the file
    with open('app/agents/sofia_agent_v2_fixed.py', 'r') as f:
        content = f.read()
    
    # Replace English phrases with Spanish
    replacements = [
        # Email request
        ('- "Great! I need your email to send the calendar invite."', 
         '- "¡Perfecto! Necesito tu correo electrónico para enviarte el enlace de la reunión."'),
        
        ('- "Perfect! To send you the Google Meet link, what\'s your email?"',
         '- "¡Excelente! Para enviarte el enlace de Google Meet, ¿cuál es tu correo?"'),
         
        # Calendar messages
        ('- "Excellent! Let me check our calendar for available times..."',
         '- "¡Excelente! Déjame revisar nuestro calendario para los horarios disponibles..."'),
    ]
    
    # Apply replacements
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Replaced: {old[:50]}...")
        else:
            print(f"⚠️  Not found: {old[:50]}...")
    
    # Add Spanish-only instruction at the beginning of the prompt
    spanish_instruction = '''IMPORTANTE: Debes responder SIEMPRE en español. NUNCA en inglés.
    
    '''
    
    # Find where to insert (after the docstring)
    prompt_start = 'context = f"""You are Sofia'
    if prompt_start in content:
        content = content.replace(
            prompt_start, 
            f'{prompt_start}\n    {spanish_instruction}'
        )
        print("✅ Added Spanish-only instruction")
    
    # Write the file back
    with open('app/agents/sofia_agent_v2_fixed.py', 'w') as f:
        f.write(content)
    
    print("\n✅ Sofia's prompt updated to Spanish!")
    print("\nNext steps:")
    print("1. Review the changes: git diff app/agents/sofia_agent_v2_fixed.py")
    print("2. Test locally: python test_with_real_ghl.py")
    print("3. Commit: git add app/agents/sofia_agent_v2_fixed.py && git commit -m 'Fix Sofia to respond only in Spanish'")
    print("4. Push: git push")

if __name__ == "__main__":
    fix_sofia_spanish()