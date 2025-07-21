#!/usr/bin/env python3
"""
Debug why intelligence node isn't extracting data
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def debug_intelligence():
    from app.intelligence.analyzer import IntelligenceAnalyzer
    from langchain_core.messages import HumanMessage
    
    # Create test state similar to what workflow would pass
    state = {
        "messages": [
            HumanMessage(content="Tengo u. Restaurante y estoy perdiendo muchas reservas pq no puedo contestar todo")
        ],
        "contact_id": "test123",
        "lead_score": 0,
        "extracted_data": {},
        "previous_custom_fields": {}
    }
    
    print("Testing Intelligence Analyzer directly...")
    print(f"Input message: {state['messages'][0].content}")
    
    analyzer = IntelligenceAnalyzer()
    
    # Test extraction directly
    extractor = analyzer.extractor
    text = state['messages'][0].content
    extracted = extractor.extract_all(text)
    
    print("\nDirect extraction results:")
    for key, value in extracted.items():
        if value:
            print(f"  {key}: {value}")
    
    # Test full analysis
    print("\nRunning full analysis...")
    enriched_state = await analyzer.analyze(state)
    
    print("\nEnriched state:")
    print(f"  Lead Score: {enriched_state.get('lead_score', 'NOT SET')}")
    print(f"  Extracted Data: {enriched_state.get('extracted_data', {})}")
    print(f"  Score Reasoning: {enriched_state.get('score_reasoning', 'NOT SET')}")
    print(f"  Suggested Agent: {enriched_state.get('suggested_agent', 'NOT SET')}")

if __name__ == "__main__":
    asyncio.run(debug_intelligence())