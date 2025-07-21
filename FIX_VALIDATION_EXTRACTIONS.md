# Fix 6: Add Validation to Prevent Nonsense Extractions

## Problem
The system extracts nonsense like:
- business_type: "negocio hola" (combining unrelated words)
- budget: "10" (extracting from time like "10:00 AM")

## Solution

### 1. Validate Business Type Extractions

```python
# app/intelligence/analyzer.py

def _validate_business_type(self, business: str) -> Optional[str]:
    """Validate extracted business type"""
    if not business:
        return None
        
    # Remove common filler words
    business = business.lower().strip()
    
    # List of invalid business types
    invalid_patterns = [
        "negocio hola", "business hello", "mi hola", "un hola",
        "negocio si", "business yes", "negocio no"
    ]
    
    if business in invalid_patterns:
        return None
    
    # Check if it contains greeting words (invalid)
    greeting_words = ["hola", "hello", "hi", "hey", "buenos", "dias", "tardes"]
    for greeting in greeting_words:
        if greeting in business.split():
            return None
    
    # Valid business types
    valid_businesses = [
        "restaurante", "restaurant", "tienda", "salon", "salón",
        "barbería", "barberia", "clinica", "clínica", "consultorio",
        "agencia", "empresa", "negocio", "local", "oficina",
        "cafetería", "cafeteria", "hotel", "spa", "gimnasio"
    ]
    
    # Check if it contains at least one valid business word
    has_valid = any(valid in business for valid in valid_businesses)
    
    if not has_valid and len(business.split()) > 1:
        # Multi-word but no valid business type
        return None
    
    return business
```

### 2. Validate Budget Extractions

```python
def _validate_budget(self, budget: str, message: str) -> Optional[str]:
    """Validate extracted budget"""
    if not budget:
        return None
    
    # Don't extract from time patterns
    time_pattern = r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)'
    if re.search(time_pattern, message):
        # Check if the number is part of a time
        if re.search(rf'{budget}:\d{{2}}', message):
            return None
    
    # Don't extract single/double digit numbers unless with currency
    if budget.isdigit() and len(budget) < 3:
        # Check if it has currency symbol nearby
        if not re.search(rf'\$\s*{budget}', message):
            return None
    
    # Don't extract from dates
    date_patterns = [
        rf'{budget}\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        rf'{budget}/(0?[1-9]|1[0-2])',  # 10/5 (October 5th)
    ]
    for pattern in date_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return None
    
    return budget
```

### 3. Update Extraction Methods

```python
def _extract_business(self, text: str) -> Optional[str]:
    """Extract business type from text - JIT optimized"""
    for pattern, confidence_type in self._compiled_patterns["business"]:
        match = pattern.search(text)
        if match:
            business = match.group(1).strip()
            # Clean common words
            business = re.sub(r'\b(un|una|el|la|mi)\b', '', business).strip()
            
            # VALIDATE before returning
            validated = self._validate_business_type(business)
            if validated:
                return validated
    return None

def _extract_budget(self, text: str) -> Optional[str]:
    """Extract budget information from text - JIT optimized"""
    for pattern_data in self._compiled_patterns["budget"]:
        # ... existing pattern matching ...
        
        if match:
            # ... format budget ...
            
            # VALIDATE before returning
            validated = self._validate_budget(budget, text)
            if validated:
                return validated
    return None
```

### 4. Add Confidence Threshold

```python
def extract_all(self, message: str, previous_data: Dict[str, Any] = None) -> Dict[str, Any]:
    # ... existing code ...
    
    # Add confidence scores only for newly extracted data
    MIN_CONFIDENCE = 0.7  # Threshold
    
    for field, value in extracted.items():
        if field != "extraction_confidence" and value:
            if value != previous_data.get(field):
                confidence = self._calculate_confidence(value, message)
                
                # Only keep extraction if confidence is high enough
                if confidence >= MIN_CONFIDENCE:
                    extracted["extraction_confidence"][field] = confidence
                else:
                    # Low confidence - revert to previous value
                    extracted[field] = previous_data.get(field)
```

## Expected Results

Before:
- "hola" → business: "negocio hola"
- "10:00 AM" → budget: "10"

After:
- "hola" → business: None (validation fails)
- "10:00 AM" → budget: None (time pattern detected)
- "tengo un restaurante" → business: "restaurante" (valid)
- "mi presupuesto es $300" → budget: "300" (valid)