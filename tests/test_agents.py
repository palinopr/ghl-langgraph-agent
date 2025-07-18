"""
Test suite for LangGraph agents
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from app.agents import SofiaAgent, CarlosAgent, MariaAgent
from app.state.conversation_state import ConversationState


class TestSofiaAgent:
    """Test cases for Sofia appointment setter agent"""
    
    @pytest.fixture
    def sofia_agent(self):
        """Create Sofia agent instance"""
        with patch('src.agents.sofia_agent.ChatOpenAI') as mock_llm:
            # Mock the LLM response
            mock_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(
                return_value=AIMessage(
                    content="I'd be happy to help you book a consultation! Let me check our available times."
                )
            )
            return SofiaAgent()
    
    @pytest.mark.asyncio
    async def test_sofia_handles_appointment_request(self, sofia_agent):
        """Test Sofia handles appointment booking requests"""
        state = {
            "messages": [HumanMessage(content="I'd like to book an appointment")],
            "contact_id": "test-123",
            "contact_info": {"name": "Test User"},
            "current_agent": None,
            "agent_responses": []
        }
        
        result = await sofia_agent.process(state)
        
        assert result["current_agent"] == "sofia"
        assert len(result["messages"]) == 1
        assert "consultation" in result["messages"][0].content.lower()
    
    def test_sofia_should_handle_appointment_keywords(self, sofia_agent):
        """Test Sofia correctly identifies appointment-related messages"""
        appointment_messages = [
            "I want to book a meeting",
            "Schedule a consultation please",
            "What times are available?",
            "Can we set up a demo?"
        ]
        
        for message in appointment_messages:
            state = {
                "messages": [HumanMessage(content=message)],
                "contact_id": "test-123"
            }
            assert sofia_agent.should_handle(state) is True
    
    def test_sofia_should_not_handle_non_appointment(self, sofia_agent):
        """Test Sofia doesn't handle non-appointment messages"""
        non_appointment_messages = [
            "What services do you offer?",
            "Tell me about your company",
            "I have a complaint"
        ]
        
        for message in non_appointment_messages:
            state = {
                "messages": [HumanMessage(content=message)],
                "contact_id": "test-123"
            }
            assert sofia_agent.should_handle(state) is False


class TestCarlosAgent:
    """Test cases for Carlos lead qualifier agent"""
    
    @pytest.fixture
    def carlos_agent(self):
        """Create Carlos agent instance"""
        with patch('src.agents.carlos_agent.ChatOpenAI') as mock_llm:
            mock_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(
                return_value=AIMessage(
                    content="Great! I'd love to learn more about your business. What industry are you in?"
                )
            )
            return CarlosAgent()
    
    @pytest.mark.asyncio
    async def test_carlos_handles_business_inquiry(self, carlos_agent):
        """Test Carlos handles business qualification"""
        state = {
            "messages": [HumanMessage(content="We're a growing SaaS company")],
            "contact_id": "test-123",
            "contact_info": {},
            "current_agent": None,
            "agent_responses": []
        }
        
        result = await carlos_agent.process(state)
        
        assert result["current_agent"] == "carlos"
        assert "business" in result["messages"][0].content.lower() or "industry" in result["messages"][0].content.lower()
    
    def test_carlos_should_handle_business_keywords(self, carlos_agent):
        """Test Carlos correctly identifies business-related messages"""
        business_messages = [
            "Our company needs marketing help",
            "What's your pricing?",
            "We have a budget of $5000",
            "Looking for marketing services"
        ]
        
        for message in business_messages:
            state = {
                "messages": [HumanMessage(content=message)],
                "contact_id": "test-123"
            }
            assert carlos_agent.should_handle(state) is True


class TestMariaAgent:
    """Test cases for Maria support agent"""
    
    @pytest.fixture
    def maria_agent(self):
        """Create Maria agent instance"""
        with patch('src.agents.maria_agent.ChatOpenAI') as mock_llm:
            mock_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(
                return_value=AIMessage(
                    content="Hello! I'm Maria, and I'm here to help. How can I assist you today?"
                )
            )
            return MariaAgent()
    
    @pytest.mark.asyncio
    async def test_maria_handles_general_inquiry(self, maria_agent):
        """Test Maria handles general support requests"""
        state = {
            "messages": [HumanMessage(content="Hello, can you help me?")],
            "contact_id": "test-123",
            "contact_info": {},
            "current_agent": None,
            "agent_responses": []
        }
        
        result = await maria_agent.process(state)
        
        assert result["current_agent"] == "maria"
        assert "help" in result["messages"][0].content.lower()
    
    def test_maria_should_handle_general_keywords(self, maria_agent):
        """Test Maria correctly identifies general support messages"""
        support_messages = [
            "Hello",
            "I have a question",
            "Can you help me?",
            "What services do you offer?"
        ]
        
        for message in support_messages:
            state = {
                "messages": [HumanMessage(content=message)],
                "contact_id": "test-123"
            }
            assert maria_agent.should_handle(state) is True
    
    @pytest.mark.asyncio
    async def test_maria_routes_to_other_agents(self, maria_agent):
        """Test Maria can route to other agents when needed"""
        # Mock response that mentions Sofia
        with patch('src.agents.maria_agent.ChatOpenAI') as mock_llm:
            mock_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(
                return_value=AIMessage(
                    content="I see you want to book an appointment. Let me connect you with Sofia who can help with that."
                )
            )
            agent = MariaAgent()
        
        state = {
            "messages": [HumanMessage(content="I want to schedule a meeting")],
            "contact_id": "test-123",
            "contact_info": {},
            "current_agent": None,
            "agent_responses": []
        }
        
        result = await agent.process(state)
        
        assert result.get("next_agent") == "sofia"
        assert result.get("routing_reason") is not None