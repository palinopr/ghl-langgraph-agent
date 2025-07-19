#!/usr/bin/env python3
"""
Fix the appointment time detection issue
"""

# The AI message that offers appointment times
ai_message = "¡Excelente! Tengo estos horarios disponibles:\n\n📅 Martes:\n• 10:00 AM\n• 2:00 PM\n\n📅 Miércoles:\n• 11:00 AM\n• 4:00 PM\n\n¿Cuál prefieres?"

content = ai_message.lower()

# Current checks
current_checks = [
    "horarios disponibles" in content,
    "10:00 am" in content,
    "tengo estos horarios" in content,
    "¿cuál prefieres?" in content
]

print("Current detection checks:")
for i, check in enumerate(current_checks):
    print(f"  {i+1}. {['horarios disponibles', '10:00 am', 'tengo estos horarios', '¿cuál prefieres?'][i]}: {check}")

# What's actually in the message
print(f"\nActual message content (lowercase):")
print(f"'{content}'")

# Check what would work
print("\nChecks that would work:")
print(f"  - 'tengo estos horarios disponibles' in content: {'tengo estos horarios disponibles' in content}")
print(f"  - '10:00 am' in content: {'10:00 am' in content}")
print(f"  - '2:00 pm' in content: {'2:00 pm' in content}")
print(f"  - 'cuál prefieres' in content: {'cuál prefieres' in content}")  # Without ¿
print(f"  - 'martes' in content: {'martes' in content}")
print(f"  - 'miércoles' in content: {'miércoles' in content}")