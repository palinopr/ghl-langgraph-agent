"""
Test script to verify LangGraph setup
"""
import asyncio
from app.workflow import create_workflow_with_memory
from langchain_core.messages import HumanMessage
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_workflow():
    """Test the LangGraph workflow with a simple conversation"""
    
    # Create workflow
    app = create_workflow_with_memory()
    
    # Test contact ID
    contact_id = "test-contact-123"
    
    # Test conversation flow
    test_messages = [
        "Hi, I'm interested in your marketing services",
        "My business is an e-commerce store selling outdoor gear",
        "I'd like to book a consultation to discuss my needs",
        "What times are available next week?"
    ]
    
    # Configuration for thread persistence
    config = {"configurable": {"thread_id": contact_id}}
    
    # Initial state
    state = {
        "messages": [],
        "contact_id": contact_id,
        "contact_info": {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+1234567890"
        },
        "current_agent": None,
        "agent_responses": []
    }
    
    # Process each message
    for message in test_messages:
        logger.info(f"\n--- Processing message: {message} ---")
        
        # Add human message to state
        state["messages"].append(HumanMessage(content=message))
        
        try:
            # Run workflow
            result = await app.ainvoke(state, config)
            
            # Extract response
            if result.get("agent_responses"):
                last_response = result["agent_responses"][-1]
                logger.info(f"Agent: {last_response['agent']}")
                logger.info(f"Response: {last_response['response']}")
            
            # Update state for next iteration
            state = result
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            break
    
    logger.info("\n--- Test completed ---")
    
    # Print final analysis
    if "analysis" in state:
        logger.info("\nFinal Analysis:")
        for agent, data in state["analysis"].items():
            logger.info(f"{agent}: {data}")


async def test_individual_agents():
    """Test individual agents directly"""
    from app.agents import SofiaAgent, CarlosAgent, MariaAgent
    from app.state.conversation_state import ConversationState
    
    logger.info("\n--- Testing Individual Agents ---")
    
    # Test Sofia
    sofia = SofiaAgent()
    sofia_state = {
        "messages": [HumanMessage(content="I'd like to book an appointment")],
        "contact_id": "test-123",
        "contact_info": {},
        "current_agent": None,
        "agent_responses": []
    }
    
    try:
        sofia_result = await sofia.process(sofia_state)
        logger.info(f"Sofia response: {sofia_result['messages'][0].content[:100]}...")
    except Exception as e:
        logger.error(f"Sofia test failed: {e}")
    
    # Test Carlos
    carlos = CarlosAgent()
    carlos_state = {
        "messages": [HumanMessage(content="We're a growing SaaS company")],
        "contact_id": "test-123",
        "contact_info": {},
        "current_agent": None,
        "agent_responses": []
    }
    
    try:
        carlos_result = await carlos.process(carlos_state)
        logger.info(f"Carlos response: {carlos_result['messages'][0].content[:100]}...")
    except Exception as e:
        logger.error(f"Carlos test failed: {e}")
    
    # Test Maria
    maria = MariaAgent()
    maria_state = {
        "messages": [HumanMessage(content="Hello, can you help me?")],
        "contact_id": "test-123",
        "contact_info": {},
        "current_agent": None,
        "agent_responses": []
    }
    
    try:
        maria_result = await maria.process(maria_state)
        logger.info(f"Maria response: {maria_result['messages'][0].content[:100]}...")
    except Exception as e:
        logger.error(f"Maria test failed: {e}")


async def main():
    """Run all tests"""
    logger.info("Starting LangGraph setup tests...")
    
    # Test individual agents
    await test_individual_agents()
    
    # Test full workflow
    await test_workflow()
    
    logger.info("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())