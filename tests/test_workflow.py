"""
Test suite for LangGraph workflow
"""
import pytest
from unittest.mock import patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from app.workflow import (
    should_continue, 
    route_to_agent, 
    create_workflow,
    create_workflow_with_memory,
    run_workflow
)
from app.state.conversation_state import ConversationState


class TestWorkflowFunctions:
    """Test workflow helper functions"""
    
    def test_should_continue_when_explicitly_false(self):
        """Test workflow stops when should_continue is False"""
        state = {"should_continue": False}
        assert should_continue(state) == "end"
    
    def test_should_continue_when_appointment_booked_and_complete(self):
        """Test workflow ends after appointment is booked and confirmed"""
        state = {
            "appointment_status": "booked",
            "messages": [
                HumanMessage(content="Book appointment"),
                AIMessage(content="Appointment booked"),
                HumanMessage(content="Thank you!")
            ]
        }
        assert should_continue(state) == "end"
    
    def test_should_continue_when_conversation_too_long(self):
        """Test workflow ends when conversation exceeds limit"""
        state = {
            "messages": [HumanMessage(content=f"Message {i}") for i in range(35)]
        }
        assert should_continue(state) == "end"
    
    def test_should_continue_default(self):
        """Test workflow continues by default"""
        state = {
            "messages": [HumanMessage(content="Hello")]
        }
        assert should_continue(state) == "orchestrator"
    
    def test_route_to_agent_explicit(self):
        """Test routing to explicitly set agent"""
        state = {"next_agent": "sofia"}
        assert route_to_agent(state) == "sofia"
    
    def test_route_to_agent_default(self):
        """Test default routing to Maria"""
        state = {}
        assert route_to_agent(state) == "maria"


class TestWorkflowCreation:
    """Test workflow creation and compilation"""
    
    def test_create_workflow(self):
        """Test basic workflow creation"""
        workflow = create_workflow()
        
        # Check nodes are added
        assert "orchestrator" in workflow.nodes
        assert "sofia" in workflow.nodes
        assert "carlos" in workflow.nodes
        assert "maria" in workflow.nodes
    
    def test_create_workflow_with_memory(self):
        """Test workflow creation with memory"""
        app = create_workflow_with_memory()
        
        # Verify it's compiled and has checkpointer
        assert app.checkpointer is not None


class TestRunWorkflow:
    """Test workflow execution"""
    
    @pytest.mark.asyncio
    async def test_run_workflow_basic(self):
        """Test basic workflow execution"""
        with patch('src.workflow.create_workflow_with_memory') as mock_create:
            # Mock the workflow app
            mock_app = AsyncMock()
            mock_app.ainvoke = AsyncMock(return_value={
                "messages": [
                    HumanMessage(content="Hello"),
                    AIMessage(content="Hi! How can I help you?")
                ],
                "agent_responses": [{
                    "agent": "maria",
                    "response": "Hi! How can I help you?",
                    "timestamp": "2024-01-01T00:00:00Z"
                }]
            })
            mock_create.return_value = mock_app
            
            # Run workflow
            result = await run_workflow(
                contact_id="test-123",
                message="Hello",
                context={"name": "Test User"}
            )
            
            # Verify result
            assert len(result["messages"]) == 2
            assert result["agent_responses"][0]["agent"] == "maria"
            
            # Verify workflow was invoked correctly
            mock_app.ainvoke.assert_called_once()
            call_args = mock_app.ainvoke.call_args[0][0]
            assert call_args["contact_id"] == "test-123"
            assert call_args["messages"][0].content == "Hello"
    
    @pytest.mark.asyncio
    async def test_run_workflow_error_handling(self):
        """Test workflow handles errors gracefully"""
        with patch('src.workflow.create_workflow_with_memory') as mock_create:
            # Mock workflow to raise error
            mock_app = AsyncMock()
            mock_app.ainvoke = AsyncMock(side_effect=Exception("Test error"))
            mock_create.return_value = mock_app
            
            # Should raise the exception
            with pytest.raises(Exception) as exc_info:
                await run_workflow(
                    contact_id="test-123",
                    message="Hello"
                )
            
            assert str(exc_info.value) == "Test error"


class TestWorkflowIntegration:
    """Integration tests for full workflow"""
    
    @pytest.mark.asyncio
    async def test_appointment_booking_flow(self):
        """Test complete appointment booking flow"""
        # This would be an integration test with mocked agents
        # For brevity, just showing the structure
        
        with patch('src.agents.orchestrator.Orchestrator.route') as mock_route:
            with patch('src.agents.sofia_agent.SofiaAgent.process') as mock_sofia:
                # Mock orchestrator to route to Sofia
                mock_route.return_value = "sofia"
                
                # Mock Sofia's response
                mock_sofia.return_value = {
                    "messages": [AIMessage(content="I'll help you book an appointment!")],
                    "current_agent": "sofia",
                    "agent_responses": [{
                        "agent": "sofia",
                        "response": "I'll help you book an appointment!",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }]
                }
                
                # Test would continue with full flow...
                pass