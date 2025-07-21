# Fix 2: Intelligence Extraction

## Problem
The intelligence layer is extracting data from conversation history instead of just the current message, causing:
- "hola" → extracts business="negocio hola", budget="10" 
- Old data polluting current analysis
- Incorrect lead scoring

## Root Cause
In `app/intelligence/analyzer.py` line 80:
```python
full_text = " ".join([message] + conversation_history[-10:])  # Last 10 messages for context
```

## Solution

### Update SpanishPatternExtractor

```python
# app/intelligence/analyzer.py

def extract_all(self, message: str, previous_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extract structured information from CURRENT message only
    
    Args:
        message: Current message to analyze
        previous_data: Previously extracted data to merge with
        
    Returns:
        Extracted data from current message
    """
    previous_data = previous_data or {}
    
    # Extract from CURRENT MESSAGE ONLY
    extracted = {
        "name": self._extract_name(message) or previous_data.get("name"),
        "business_type": self._extract_business(message) or previous_data.get("business_type"),
        "budget": self._extract_budget(message) or previous_data.get("budget"),
        "goal": self._extract_goal(message) or previous_data.get("goal"),
        "email": self._extract_email(message) or previous_data.get("email"),
        "phone": self._extract_phone(message) or previous_data.get("phone"),
        "extraction_confidence": {}
    }
    
    # Add confidence scores
    for field, value in extracted.items():
        if field != "extraction_confidence" and value:
            # Only add confidence if newly extracted (not from previous)
            if value != previous_data.get(field):
                extracted["extraction_confidence"][field] = self._calculate_confidence(value, message)
    
    return extracted
```

### Update Intelligence Analyzer

```python
# app/intelligence/analyzer.py

async def analyze(self, state: ConversationState) -> Dict[str, Any]:
    """
    Analyze CURRENT message and extract intelligence
    """
    # Get current message
    messages = state.get("messages", [])
    if not messages:
        return state
        
    current_message = messages[-1].content if messages else ""
    
    # Get previous score and data
    previous_score = state.get("lead_score", 0)
    previous_data = state.get("extracted_data", {})
    
    # Extract from CURRENT MESSAGE ONLY, merge with previous
    extracted = self.extractor.extract_all(current_message, previous_data)
    
    # Check for budget confirmation (still needs context)
    budget_confirmation = {}
    if len(messages) >= 2:
        last_assistant_msg = ""
        for msg in reversed(messages[:-1]):
            if isinstance(msg, AIMessage):
                last_assistant_msg = msg.content
                break
                
        budget_confirmation = self.budget_detector.detect_confirmation(
            current_message, last_assistant_msg
        )
        
        if budget_confirmation.get("budget_confirmed"):
            extracted["budget"] = budget_confirmation["amount"]
    
    # Calculate score based on ALL collected data (cumulative)
    score, reasoning, breakdown = self.scorer.calculate_score(
        extracted,  # All data collected so far
        previous_score,
        len(messages)
    )
    
    # ... rest remains the same
```

## Testing

### Before Fix
```
Customer: "hola"
Extraction looks at: "hola" + last 10 messages from history
Extracts: business="negocio hola" (from old messages)
Score: 9/10
```

### After Fix
```
Customer: "hola"
Extraction looks at: "hola" only
Extracts: Nothing (correct!)
Previous data: Preserved if any
Score: 1-2 (correct!)
```

## Key Changes
1. `extract_all()` only analyzes current message
2. Previous data is preserved and merged
3. Confidence scores only for NEW extractions
4. Budget confirmation still checks context (correctly)
5. Score calculation uses cumulative data