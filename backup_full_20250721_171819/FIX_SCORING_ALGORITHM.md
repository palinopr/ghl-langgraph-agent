# Fix 5: Scoring Algorithm (1-10 Scale)

## Current Scoring Logic
The scoring is actually reasonable:
- Base: 1 point
- Name: 2 points  
- Business: 2 points
- Goal: 2 points
- Budget: 2-3 points
- Email: 1 point
- Phone: 1 point
- Engagement: 1 point
- Max: 10-12 points (capped at 10)

## The Real Problem
The high scores (9/10 for "hola") were caused by:
1. Extracting from polluted conversation history
2. Finding old data like "negocio", "budget: 10" from previous conversations

## With Our Fixes
Now that we:
1. Only extract from current message
2. Preserve previous data properly
3. Don't look at old conversations

The scoring should work correctly:
- "hola" → No extraction → Score 1-2
- "tengo un restaurante" → Business extracted → Score 3-4
- "estoy perdiendo reservas" → Goal extracted → Score 5-6
- "$300 está bien" → Budget confirmed → Score 7-8
- Email provided → Score 8-9
- Ready to book → Score 9-10

## Minor Adjustments

```python
# Make scoring more conservative for early messages
def calculate_score(self, extracted_data: Dict[str, Any], previous_score: int = 0, conversation_length: int = 0) -> Tuple[int, str, Dict[str, int]]:
    score_breakdown = {
        "base": 1,
        "name": 0,
        "business": 0,
        "goal": 0,
        "budget": 0,
        "email": 0,
        "phone": 0,
        "engagement": 0
    }
    
    reasoning_parts = []
    
    # Name: 1 point (reduced from 2)
    if extracted_data.get("name"):
        score_breakdown["name"] = 1
        reasoning_parts.append("has name")
    
    # Business: 2 points
    if extracted_data.get("business_type"):
        score_breakdown["business"] = 2
        reasoning_parts.append(f"has business ({extracted_data['business_type']})")
    
    # Goal/Problem: 1 point (reduced from 2)
    if extracted_data.get("goal"):
        score_breakdown["goal"] = 1
        reasoning_parts.append("has goal/problem")
    
    # Budget: 2-3 points
    if extracted_data.get("budget"):
        budget_str = str(extracted_data["budget"])
        if any(x in budget_str for x in ["300", "400", "500"]) or re.search(r'\d{3,}', budget_str):
            score_breakdown["budget"] = 3
            reasoning_parts.append(f"budget confirmed ({budget_str})")
        else:
            score_breakdown["budget"] = 1  # Reduced from 2
            reasoning_parts.append(f"budget mentioned ({budget_str})")
    
    # Email: 1 point
    if extracted_data.get("email") and extracted_data["email"] != "none":
        score_breakdown["email"] = 1
        reasoning_parts.append("has email")
    
    # Phone: 0 points (phone is automatic from GHL)
    # Removed phone scoring
    
    # Engagement: 1 point only for long conversations
    if conversation_length > 10:  # Increased from 5
        score_breakdown["engagement"] = 1
        reasoning_parts.append("highly engaged")
    
    # Calculate total
    total_score = sum(score_breakdown.values())
    
    # Apply persistence rule
    final_score = max(total_score, previous_score)
    
    if final_score > total_score:
        reasoning_parts.append(f"maintained previous score ({previous_score})")
    
    # Cap at 10
    final_score = min(10, final_score)
    
    reasoning = f"Score {final_score}: " + ", ".join(reasoning_parts) if reasoning_parts else "minimal information"
    
    return final_score, reasoning, score_breakdown
```

## Expected Scores After Fix

1. **Just "hola"**: Score 1 (base only)
2. **"Soy Maria"**: Score 2 (base + name)
3. **"tengo un restaurante"**: Score 4 (base + name + business)
4. **"estoy perdiendo clientes"**: Score 5 (+ goal)
5. **"mi presupuesto es $300"**: Score 8 (+ budget confirmed)
6. **Provides email**: Score 9 (+ email)
7. **Long engaged conversation**: Score 10 (+ engagement)

## Routing Thresholds
- 1-4: Maria (cold lead)
- 5-7: Carlos (warm lead)
- 8-10: Sofia (hot lead)

This ensures proper agent assignment based on actual qualification level.