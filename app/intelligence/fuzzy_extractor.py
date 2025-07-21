"""
Fuzzy business extraction with typo tolerance using RapidFuzz
"""
from rapidfuzz import fuzz, process
from typing import Dict, List, Tuple, Optional
import re
from app.utils.simple_logger import get_logger

logger = get_logger("fuzzy_extractor")

class FuzzyBusinessExtractor:
    """Extract business types with typo tolerance"""
    
    # Business vocabulary with variations
    BUSINESS_TYPES = {
        "restaurante": ["restaurante", "restaurant", "resto", "restauran", "restorante"],
        "tienda": ["tienda", "store", "shop", "tiendita"],
        "salon": ["salon", "salón", "saloon", "peluqueria", "peluquería"],
        "barberia": ["barbería", "barberia", "barber", "barbero"],
        "clinica": ["clínica", "clinica", "clinic", "consultorio", "consulta"],
        "agencia": ["agencia", "agency", "oficina"],
        "hotel": ["hotel", "motel", "hostal", "hospedaje"],
        "gym": ["gym", "gimnasio", "fitness", "crossfit"],
        "spa": ["spa", "masaje", "masajes"],
        "cafe": ["café", "cafe", "cafetería", "cafeteria", "coffee"],
        "pizzeria": ["pizzería", "pizzeria", "pizza"],
        "panaderia": ["panadería", "panaderia", "bakery", "pan"],
        "farmacia": ["farmacia", "pharmacy", "drogueria"],
        "negocio": ["negocio", "business", "empresa", "comercio"],
        "bar": ["bar", "cantina", "cerveceria", "cervecería"],
        "taller": ["taller", "mecanico", "mecánico", "garage"],
        "estetica": ["estética", "estetica", "belleza", "beauty"],
        "dentista": ["dentista", "dental", "odontologia", "odontología"]
    }
    
    def __init__(self):
        # Build lookup tables
        self.all_business_words = []
        self.word_to_type = {}
        
        for business_type, variations in self.BUSINESS_TYPES.items():
            for word in variations:
                self.all_business_words.append(word)
                self.word_to_type[word] = business_type
    
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
        best_word = None
        
        # Check each word against business vocabulary
        for word in words:
            # Skip very short words
            if len(word) < 4:
                continue
            
            # Skip common words
            if word in ["tengo", "quiero", "necesito", "para", "estoy", "hola"]:
                continue
                
            # Use RapidFuzz to find best match
            match_result = process.extractOne(
                word, 
                self.all_business_words,
                scorer=fuzz.WRatio,
                score_cutoff=threshold
            )
            
            if match_result:
                matched_word, score, _ = match_result
                if score > best_score:
                    best_score = score
                    best_match = self.word_to_type[matched_word]
                    best_word = word
        
        if best_match:
            # Convert score to confidence (0-1)
            confidence = best_score / 100.0
            logger.info(f"Fuzzy match: '{best_word}' → '{best_match}' (score: {best_score})")
            return (best_match, confidence)
        
        return None
    
    def extract_with_context(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Extract business with context clues for better accuracy
        """
        text_lower = text.lower()
        
        # Context patterns that indicate business
        context_patterns = [
            (r"tengo un[a]?\s+(\w+)", 0.9),           # "tengo un X"
            (r"mi\s+(\w+)", 0.85),                    # "mi X"
            (r"en mi\s+(\w+)", 0.85),                 # "en mi X"
            (r"para mi\s+(\w+)", 0.85),               # "para mi X"
            (r"soy dueñ[oa] de un[a]?\s+(\w+)", 0.95), # "soy dueño de un X"
            (r"trabajo en un[a]?\s+(\w+)", 0.9),      # "trabajo en un X"
            (r"negocio de\s+(\w+)", 0.9),             # "negocio de X"
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
                    boosted_confidence = min(confidence + context_boost * 0.1, 1.0)
                    logger.info(f"Context boost applied: {confidence:.2f} → {boosted_confidence:.2f}")
                    return (business_type, boosted_confidence)
        
        # Fallback to regular extraction
        return self.extract_business_fuzzy(text, threshold=80)


# Testing
if __name__ == "__main__":
    extractor = FuzzyBusinessExtractor()
    
    test_cases = [
        "tengo un reaturante",        # Typo: reaturante
        "mi resturante",              # Typo: resturante  
        "soy dueño de una peluqeria", # Typo: peluqeria (peluquería)
        "trabajo en un gimansio",     # Typo: gimansio (gimnasio)
        "mi negosio",                 # Typo: negosio (negocio)
        "una tieda de ropa",          # Typo: tieda (tienda)
        "mi clinica dental",          # Correct spelling
        "tengo un café",              # Accent handling
        "un restarante italiano",     # Typo: restarante
        "para mi restorant"           # Typo: restorant
    ]
    
    print("Testing Fuzzy Business Extraction:")
    print("-" * 50)
    
    for test in test_cases:
        result = extractor.extract_with_context(test)
        if result:
            business, confidence = result
            print(f"✅ '{test}' → {business} (confidence: {confidence:.2f})")
        else:
            print(f"❌ '{test}' → No business detected")