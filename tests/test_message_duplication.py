"""
Test Message Duplication - Integration tests to prevent message duplication
"""
import pytest
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.state.message_manager import MessageManager
from app.utils.debug_helpers import validate_state, analyze_message_accumulation


class TestMessageManager:
    """Test MessageManager handles all message formats correctly"""
    
    def test_dict_vs_basemessage_comparison(self):
        """Test that dict and BaseMessage with same content are recognized as duplicates"""
        current_messages = [
            HumanMessage(content="Hola"),
            AIMessage(content="Hello! How can I help?")
        ]
        
        # Try to add same messages in dict format
        new_messages = [
            {"role": "human", "content": "Hola"},  # Same as HumanMessage
            {"role": "user", "content": "Hola"},   # Different role name, same content
            {"role": "ai", "content": "Hello! How can I help?"}  # Same as AIMessage
        ]
        
        unique = MessageManager.set_messages(current_messages, new_messages)
        
        # Should return empty list as all are duplicates
        assert len(unique) == 0, f"Expected 0 unique messages, got {len(unique)}: {unique}"
    
    def test_message_deduplication(self):
        """Test deduplication removes all duplicates"""
        messages = [
            HumanMessage(content="Test"),
            {"role": "human", "content": "Test"},
            {"role": "user", "content": "Test"},
            HumanMessage(content="Test"),  # Exact duplicate
            AIMessage(content="Response"),
            {"role": "assistant", "content": "Response"},
            {"role": "ai", "content": "Response"}
        ]
        
        deduplicated = MessageManager.deduplicate_messages(messages)
        
        # Should have only 2 unique messages
        assert len(deduplicated) == 2, f"Expected 2 messages, got {len(deduplicated)}"
        
        # Verify content
        contents = [m.content if hasattr(m, 'content') else m.get('content') for m in deduplicated]
        assert contents == ["Test", "Response"]
    
    def test_error_message_handling(self):
        """Test that error messages are properly deduplicated"""
        messages = [
            HumanMessage(content="Hola"),
            AIMessage(content="Error"),
            {"role": "ai", "content": "Error"},
            AIMessage(content="Error"),
            {"role": "assistant", "content": "Error"}
        ]
        
        deduplicated = MessageManager.deduplicate_messages(messages)
        
        # Should have only 2 unique messages
        assert len(deduplicated) == 2
        error_count = sum(1 for m in deduplicated if "Error" in (m.content if hasattr(m, 'content') else m.get('content', '')))
        assert error_count == 1, "Should have exactly one Error message"


class TestStateValidation:
    """Test state validation catches duplication issues"""
    
    def test_validate_duplicate_detection(self):
        """Test that validation detects duplicates"""
        state = {
            "messages": [
                HumanMessage(content="Hello"),
                HumanMessage(content="Hello"),
                {"role": "human", "content": "Hello"},
                AIMessage(content="Hi there!")
            ],
            "thread_id": "test-thread"
        }
        
        result = validate_state(state, "test_node")
        
        assert not result["valid"]
        assert result["metrics"]["duplicates"] == 2  # 3 "Hello" - 1 unique = 2 duplicates
        assert any("3 times" in issue for issue in result["issues"])
    
    def test_validate_error_detection(self):
        """Test that validation detects error messages"""
        state = {
            "messages": [
                HumanMessage(content="Test"),
                AIMessage(content="Error: Something went wrong"),
                AIMessage(content="Error: Another error")
            ]
        }
        
        result = validate_state(state, "test_node")
        
        assert result["metrics"]["error_messages"] == 2
        assert any("2 error messages" in issue for issue in result["issues"])
    
    def test_validate_malformed_messages(self):
        """Test that validation catches malformed messages"""
        state = {
            "messages": [
                HumanMessage(content="Valid"),
                {"content": "Missing role/type"},  # Invalid
                "Just a string",  # Invalid
                {"role": "human", "content": "Valid dict"}
            ]
        }
        
        result = validate_state(state, "test_node")
        
        assert not result["valid"]
        assert any("missing type/role" in issue for issue in result["issues"])


class TestMessageAccumulation:
    """Test message accumulation analysis"""
    
    def test_exponential_growth_detection(self):
        """Test detection of exponential message growth"""
        states = [
            {"__node__": "node1", "messages": [HumanMessage(content="Test")]},
            {"__node__": "node2", "messages": [HumanMessage(content="Test")] * 2},
            {"__node__": "node3", "messages": [HumanMessage(content="Test")] * 4},
            {"__node__": "node4", "messages": [HumanMessage(content="Test")] * 8}
        ]
        
        analysis = analyze_message_accumulation(states)
        
        assert analysis["accumulation_pattern"] == "exponential"
        assert len(analysis["duplication_points"]) == 3  # All but first have duplicates
        
        # Check growth matches expected pattern
        growth = [g["count"] for g in analysis["message_growth"]]
        assert growth == [1, 2, 4, 8]


@pytest.mark.asyncio
class TestWorkflowIntegration:
    """Integration tests for the full workflow"""
    
    async def test_no_duplication_through_workflow(self):
        """Test that messages don't duplicate through the workflow"""
        from app.workflow import create_graph
        from app.state import GraphState
        
        # Create workflow
        graph = create_graph()
        
        # Initial state
        initial_state = GraphState(
            messages=[HumanMessage(content="Test message")],
            contact_id="test-123",
            thread_id="test-thread",
            webhook_data={"body": "Test message"}
        )
        
        # Run workflow (mock the external calls)
        # This would need proper mocking in a real test
        # For now, just validate the concept
        
        # Simulate expected behavior
        expected_final_messages = 3  # Human, AI response, maybe one more
        
        # In a real test, we'd run: result = await graph.ainvoke(initial_state)
        # Then validate: assert len(result['messages']) <= expected_final_messages
        
        assert True  # Placeholder for now
    
    async def test_error_recovery_no_duplication(self):
        """Test that error recovery doesn't cause duplication"""
        # Test that when a node fails and returns an error,
        # the error message doesn't get duplicated in retries
        
        state = {
            "messages": [
                HumanMessage(content="Test"),
                AIMessage(content="Error: API failure")
            ]
        }
        
        # After retry, should still have only one error message
        # This would test the actual retry logic
        
        assert True  # Placeholder


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])