#!/usr/bin/env python3
"""
Verify ALL fixes are working correctly
"""
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

# Disable tracing to avoid issues
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'

async def test_all_fixes():
    """Test that all components are working"""
    
    print("🔍 VERIFYING ALL FIXES")
    print("="*60)
    
    results = []
    
    # Test 1: Extraction logic
    print("\n1️⃣ Testing Extraction Logic...")
    try:
        from app.intelligence.analyzer import SpanishPatternExtractor, LeadScorer
        
        extractor = SpanishPatternExtractor()
        scorer = LeadScorer()
        
        # Test restaurant abbreviation
        message = "Tengo u. Restaurante y estoy perdiendo muchas reservas pq no puedo contestar todo"
        extracted = extractor.extract_all(message)
        score, reasoning, _ = scorer.calculate_score(extracted)
        
        if extracted.get('business_type') == 'restaurante' and score >= 5:
            print("   ✅ Extraction: Restaurant + problem detected, score 5+")
            results.append(("Extraction", True))
        else:
            print(f"   ❌ Extraction: Got {extracted}, score {score}")
            results.append(("Extraction", False))
            
    except Exception as e:
        print(f"   ❌ Extraction Error: {e}")
        results.append(("Extraction", False))
    
    # Test 2: Intelligence Analyzer
    print("\n2️⃣ Testing Intelligence Analyzer...")
    try:
        from app.intelligence.analyzer import IntelligenceAnalyzer
        from langchain_core.messages import HumanMessage
        
        analyzer = IntelligenceAnalyzer()
        state = {
            "messages": [HumanMessage(content=message)],
            "contact_id": "test123",
            "lead_score": 0,
            "extracted_data": {},
            "previous_custom_fields": {}
        }
        
        enriched = await analyzer.analyze(state)
        
        if enriched.get('lead_score', 0) >= 5:
            print(f"   ✅ Intelligence: Score {enriched['lead_score']}, extracted {enriched.get('extracted_data', {})}")
            results.append(("Intelligence", True))
        else:
            print(f"   ❌ Intelligence: Score only {enriched.get('lead_score', 0)}")
            results.append(("Intelligence", False))
            
    except Exception as e:
        print(f"   ❌ Intelligence Error: {e}")
        results.append(("Intelligence", False))
    
    # Test 3: TracedOperation
    print("\n3️⃣ Testing TracedOperation...")
    try:
        from app.utils.tracing import TracedOperation
        
        async with TracedOperation("test_operation", metadata={"test": "value"}):
            pass
        
        print("   ✅ TracedOperation: No errors")
        results.append(("TracedOperation", True))
            
    except Exception as e:
        print(f"   ❌ TracedOperation Error: {e}")
        results.append(("TracedOperation", False))
    
    # Test 4: Tool Creation
    print("\n4️⃣ Testing Tool Creation...")
    try:
        from app.tools.agent_tools_v2 import create_handoff_tool_for_supervisor
        
        tool = create_handoff_tool_for_supervisor("test_agent")
        if tool:
            print("   ✅ Tool Creation: Supervisor handoff tool created")
            results.append(("ToolCreation", True))
        else:
            print("   ❌ Tool Creation: Failed to create tool")
            results.append(("ToolCreation", False))
            
    except Exception as e:
        print(f"   ❌ Tool Creation Error: {e}")
        results.append(("ToolCreation", False))
    
    # Test 5: GHL Client
    print("\n5️⃣ Testing GHL Client...")
    try:
        from app.tools.ghl_client import ghl_client
        
        # Check if the right methods exist
        has_get_contact = hasattr(ghl_client, 'get_contact') or hasattr(ghl_client, 'get_contact_details')
        has_messages = hasattr(ghl_client, 'get_conversation_messages')
        
        if has_get_contact and has_messages:
            print("   ✅ GHL Client: Required methods exist")
            results.append(("GHLClient", True))
        else:
            print(f"   ❌ GHL Client: Missing methods")
            results.append(("GHLClient", False))
            
    except Exception as e:
        print(f"   ❌ GHL Client Error: {e}")
        results.append(("GHLClient", False))
    
    # Test 6: Full Workflow
    print("\n6️⃣ Testing Full Workflow...")
    try:
        from app.workflow import workflow
        
        state = {
            "messages": [HumanMessage(content=message)],
            "contact_id": "test_workflow",
            "webhook_data": {"message": message, "contactId": "test_workflow"},
            "extracted_data": {},
            "lead_score": 0,
            "contact_info": {"id": "test_workflow", "firstName": "Test"},
            "conversation_history": [],
            "previous_custom_fields": {}
        }
        
        config = {"configurable": {"thread_id": f"test_{datetime.now().timestamp()}"}}
        
        # Try to run workflow
        final_state = await workflow.ainvoke(state, config)
        
        score = final_state.get('lead_score', 0)
        extracted = final_state.get('extracted_data', {})
        
        if score >= 5 and 'restaurante' in str(extracted).lower():
            print(f"   ✅ Workflow: Score {score}, extracted business type")
            results.append(("Workflow", True))
        else:
            print(f"   ❌ Workflow: Score {score}, extracted {extracted}")
            results.append(("Workflow", False))
            
    except Exception as e:
        print(f"   ❌ Workflow Error: {e}")
        results.append(("Workflow", False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for component, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {component}")
    
    print(f"\nTotal: {passed}/{total} components working")
    
    if passed == total:
        print("\n🎉 ALL FIXES VERIFIED! The system should work correctly now.")
    else:
        print(f"\n⚠️  {total - passed} components still have issues.")
    
    return passed == total

if __name__ == "__main__":
    all_good = asyncio.run(test_all_fixes())
    exit(0 if all_good else 1)