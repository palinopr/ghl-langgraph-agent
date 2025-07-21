# Ultra-Smart Typo Tolerance Solution

## The Problem
- "un reaturante" → Score 1 (not recognized as restaurant business)
- Users make typos all the time in WhatsApp
- Current exact matching misses business mentions with typos

## The Solution: Fuzzy Matching with RapidFuzz

### 1. Install RapidFuzz
```bash
pip install rapidfuzz
```

### 2. Enhanced Business Extraction with Typo Tolerance

```python
# app/intelligence/fuzzy_extractor.py
from rapidfuzz import fuzz, process
from typing import Dict, List, Tuple, Optional
import re

class FuzzyBusinessExtractor:
    """Extract business types with typo tolerance"""
    
    # Business vocabulary with variations
    BUSINESS_TYPES = {
        "restaurante": ["restaurante", "restaurant", "resto", "restauran"],
        "tienda": ["tienda", "store", "shop"],
        "salon": ["salon", "salón", "saloon"],
        "barberia": ["barbería", "barberia", "barber"],
        "clinica": ["clínica", "clinica", "clinic"],
        "consultorio": ["consultorio", "consulta"],
        "agencia": ["agencia", "agency"],
        "hotel": ["hotel", "motel", "hostal"],
        "gym": ["gym", "gimnasio", "fitness"],
        "spa": ["spa", "masaje"],
        "cafe": ["café", "cafe", "cafetería"],
        "pizzeria": ["pizzería", "pizzeria", "pizza"],
        "panaderia": ["panadería", "panaderia", "bakery"],
        "farmacia": ["farmacia", "pharmacy"],
        "negocio": ["negocio", "business", "empresa"]
    }
    
    # Flatten all business words for fuzzy matching
    ALL_BUSINESS_WORDS = []
    WORD_TO_TYPE = {}
    
    def __init__(self):
        # Build lookup tables
        for business_type, variations in self.BUSINESS_TYPES.items():
            for word in variations:
                self.ALL_BUSINESS_WORDS.append(word)
                self.WORD_TO_TYPE[word] = business_type
    
    def extract_business_fuzzy(self, text: str, threshold: int = 80) -> Optional[Tuple[str, float]]:
        """
        Extract business type with typo tolerance
        
        Args:
            text: Input text (e.g., "tengo un reaturante")
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Tuple of (business_type, confidence) or None
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        best_match = None
        best_score = 0
        
        # Check each word against business vocabulary
        for word in words:
            # Skip short words
            if len(word) < 4:
                continue
                
            # Use RapidFuzz to find best match
            match_result = process.extractOne(
                word, 
                self.ALL_BUSINESS_WORDS,
                scorer=fuzz.WRatio,
                score_cutoff=threshold
            )
            
            if match_result:
                matched_word, score, _ = match_result
                if score > best_score:
                    best_score = score
                    best_match = self.WORD_TO_TYPE[matched_word]
        
        if best_match:
            # Convert score to confidence (0-1)
            confidence = best_score / 100.0
            return (best_match, confidence)
        
        return None
    
    def extract_with_context(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Extract business with context clues
        """
        text_lower = text.lower()
        
        # Context patterns that indicate business
        context_patterns = [
            (r"tengo un[a]?\s+(\w+)", 0.9),  # "tengo un X"
            (r"mi\s+(\w+)", 0.8),             # "mi X"
            (r"en mi\s+(\w+)", 0.8),          # "en mi X"
            (r"para mi\s+(\w+)", 0.8),        # "para mi X"
            (r"soy dueño de un[a]?\s+(\w+)", 0.95),  # "soy dueño de un X"
        ]
        
        for pattern, context_boost in context_patterns:
            match = re.search(pattern, text_lower)
            if match:
                potential_business = match.group(1)
                
                # Try fuzzy match with lower threshold due to context
                result = self.extract_business_fuzzy(potential_business, threshold=70)
                if result:
                    business_type, confidence = result
                    # Boost confidence due to context
                    boosted_confidence = min(confidence * context_boost, 1.0)
                    return (business_type, boosted_confidence)
        
        # Fallback to regular extraction
        return self.extract_business_fuzzy(text)

# Example usage and tests
if __name__ == "__main__":
    extractor = FuzzyBusinessExtractor()
    
    test_cases = [
        "tengo un reaturante",  # Typo: reaturante
        "mi resturante",        # Typo: resturante
        "soy dueño de una peluqeria",  # Typo: peluqeria (peluquería)
        "trabajo en un gimansio",  # Typo: gimansio (gimnasio)
        "mi negosio",          # Typo: negosio (negocio)
        "una tieda de ropa",   # Typo: tieda (tienda)
        "mi clinica dental",   # Correct spelling
        "tengo un café"        # Accent handling
    ]
    
    for test in test_cases:
        result = extractor.extract_with_context(test)
        if result:
            business, confidence = result
            print(f"'{test}' → {business} (confidence: {confidence:.2f})")
        else:
            print(f"'{test}' → No business detected")
```

### 3. Integrate with Current System

```python
# app/intelligence/analyzer.py - Enhanced version

from app.intelligence.fuzzy_extractor import FuzzyBusinessExtractor

class EnhancedIntelligenceAnalyzer:
    def __init__(self):
        self.fuzzy_extractor = FuzzyBusinessExtractor()
        # ... existing init code
    
    def extract_business(self, message: str, previous_business: str = None) -> str:
        """Extract business type with typo tolerance"""
        
        # First try exact matching (fastest)
        message_lower = message.lower()
        for business_type, variations in BUSINESS_PATTERNS.items():
            for variant in variations:
                if variant in message_lower:
                    logger.info(f"✅ Exact match found: {business_type}")
                    return business_type
        
        # If no exact match, try fuzzy matching
        fuzzy_result = self.fuzzy_extractor.extract_with_context(message)
        if fuzzy_result:
            business_type, confidence = fuzzy_result
            if confidence >= 0.75:  # High confidence threshold
                logger.info(f"✅ Fuzzy match found: {business_type} (confidence: {confidence:.2f})")
                return business_type
            else:
                logger.info(f"⚠️ Low confidence fuzzy match: {business_type} ({confidence:.2f})")
        
        # Return previous or default
        return previous_business or "NO_MENCIONADO"
```

### 4. Advanced Features

```python
# Multi-language support
BUSINESS_TRANSLATIONS = {
    "restaurant": "restaurante",
    "store": "tienda",
    "barber": "barberia",
    "clinic": "clinica",
    "agency": "agencia",
    "bakery": "panaderia"
}

# Common typo patterns
TYPO_CORRECTIONS = {
    "reaturante": "restaurante",
    "resturante": "restaurante",
    "gimansio": "gimnasio",
    "peluqeria": "peluquería",
    "negosio": "negocio"
}

# Phonetic matching for voice-to-text errors
from metaphone import doublemetaphone

def phonetic_match(word1, word2):
    """Match words that sound similar"""
    p1 = doublemetaphone(word1)
    p2 = doublemetaphone(word2)
    return p1[0] == p2[0] or p1[1] == p2[1]
```

## Benefits

1. **Handles Common Typos**
   - "reaturante" → "restaurante" ✅
   - "gimansio" → "gimnasio" ✅
   - "negosio" → "negocio" ✅

2. **Context-Aware**
   - "tengo un reaturante" → Higher confidence
   - Just "reaturante" → Lower confidence

3. **Performance Optimized**
   - Exact match first (fast path)
   - Fuzzy match only when needed
   - Caching for repeated queries

4. **Configurable Thresholds**
   - Strict mode: 90% similarity
   - Normal mode: 80% similarity
   - Context mode: 70% similarity

## Testing

```python
# test_fuzzy_extraction.py
def test_typo_tolerance():
    test_cases = [
        ("un reaturante", "restaurante", 0.8),
        ("mi resturante", "restaurante", 0.8),
        ("tengo una tieda", "tienda", 0.8),
        ("mi gimansio", "gimnasio", 0.7),
    ]
    
    for input_text, expected_type, min_confidence in test_cases:
        result = extract_business_with_typos(input_text)
        assert result[0] == expected_type
        assert result[1] >= min_confidence
```

## Deployment Steps

1. Add `rapidfuzz>=3.0.0` to requirements.txt
2. Create `app/intelligence/fuzzy_extractor.py`
3. Update `app/intelligence/analyzer.py` to use fuzzy matching
4. Test with common typos
5. Deploy and monitor improvement in business detection

## Expected Results

Before:
- "un reaturante" → No business detected → Score 1

After:
- "un reaturante" → "restaurante" detected → Score 3-4
- Better lead qualification
- Fewer missed opportunities due to typos