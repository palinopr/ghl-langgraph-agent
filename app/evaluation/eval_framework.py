"""
Evaluation Framework for LangGraph Multi-Agent System
Tests routing accuracy, response quality, and task completion
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage
from app.utils.simple_logger import get_logger

logger = get_logger("eval_framework")


class EvalMetric(Enum):
    """Evaluation metrics"""
    ROUTING_ACCURACY = "routing_accuracy"
    RESPONSE_QUALITY = "response_quality"
    TASK_COMPLETION = "task_completion"
    ESCALATION_APPROPRIATENESS = "escalation_appropriateness"
    STATE_FIELD_COUNT = "state_field_count"
    RESPONSE_TIME = "response_time"
    SPANISH_CONSISTENCY = "spanish_consistency"


@dataclass
class TestCase:
    """Test case for evaluation"""
    id: str
    description: str
    messages: List[str]  # Sequence of user messages
    expected_agent: str  # Expected final agent
    expected_score_range: Tuple[int, int]  # Expected score range
    expected_outcome: str  # Expected outcome description
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of a single evaluation"""
    test_case_id: str
    success: bool
    actual_agent: str
    actual_score: int
    messages_exchanged: int
    response_time_ms: float
    errors: List[str] = field(default_factory=list)
    metrics: Dict[EvalMetric, float] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)


class MultiAgentEvaluator:
    """Evaluator for multi-agent system"""
    
    def __init__(self, workflow):
        self.workflow = workflow
        self.test_cases = self._create_test_cases()
        
    def _create_test_cases(self) -> List[TestCase]:
        """Create comprehensive test cases"""
        return [
            # Cold lead tests (Maria)
            TestCase(
                id="cold_1",
                description="New contact asking general questions",
                messages=["Hola, ¿qué hacen ustedes?"],
                expected_agent="maria",
                expected_score_range=(1, 3),
                expected_outcome="Maria provides general information"
            ),
            TestCase(
                id="cold_2",
                description="Contact just providing name",
                messages=["Mi nombre es Juan"],
                expected_agent="maria",
                expected_score_range=(2, 3),
                expected_outcome="Maria asks about business"
            ),
            
            # Warm lead tests (Carlos)
            TestCase(
                id="warm_1",
                description="Business owner exploring options",
                messages=["Tengo un restaurante y busco automatización"],
                expected_agent="carlos",
                expected_score_range=(5, 7),
                expected_outcome="Carlos qualifies budget"
            ),
            TestCase(
                id="warm_2",
                description="Multi-message qualification",
                messages=[
                    "Hola, soy Pedro",
                    "Tengo una tienda online",
                    "Quiero mejorar mis ventas"
                ],
                expected_agent="carlos",
                expected_score_range=(5, 7),
                expected_outcome="Carlos explores needs and budget"
            ),
            
            # Hot lead tests (Sofia)
            TestCase(
                id="hot_1",
                description="Ready to book with all info",
                messages=["Soy María, tengo un salón de belleza, mi presupuesto es $500/mes y quiero agendar una cita"],
                expected_agent="sofia",
                expected_score_range=(8, 10),
                expected_outcome="Sofia offers appointment slots"
            ),
            TestCase(
                id="hot_2",
                description="Budget confirmation flow",
                messages=[
                    "Me llamo Carlos y tengo una barbería",
                    "Mi presupuesto es como unos $300 al mes",
                    "Sí, confirmo ese presupuesto"
                ],
                expected_agent="sofia",
                expected_score_range=(8, 10),
                expected_outcome="Sofia books appointment"
            ),
            
            # Escalation tests
            TestCase(
                id="escalation_1",
                description="Maria escalates qualified lead",
                messages=[
                    "Hola, soy Ana",
                    "Tengo un restaurante",
                    "Mi presupuesto es $400 mensuales"
                ],
                expected_agent="carlos",
                expected_score_range=(6, 8),
                expected_outcome="Maria escalates to Carlos after budget mention"
            ),
            TestCase(
                id="escalation_2",
                description="Carlos escalates hot lead",
                messages=[
                    "Soy Luis con una clínica dental",
                    "Presupuesto de $500",
                    "Sí, quiero agendar ya, luis@clinica.com"
                ],
                expected_agent="sofia",
                expected_score_range=(8, 10),
                expected_outcome="Carlos escalates to Sofia for appointment"
            ),
            
            # Edge cases
            TestCase(
                id="edge_1",
                description="Typos and misspellings",
                messages=["Ola, tengo um resturante"],
                expected_agent="carlos",
                expected_score_range=(4, 6),
                expected_outcome="System handles typos correctly"
            ),
            TestCase(
                id="edge_2",
                description="Mixed language",
                messages=["Hello, I have una tienda"],
                expected_agent="maria",
                expected_score_range=(3, 5),
                expected_outcome="System responds in Spanish"
            )
        ]
    
    async def evaluate_single(self, test_case: TestCase) -> EvalResult:
        """Evaluate a single test case"""
        logger.info(f"Evaluating test case: {test_case.id} - {test_case.description}")
        
        start_time = datetime.now()
        errors = []
        trace = []
        
        try:
            # Create initial state
            state = {
                "messages": [],
                "contact_id": f"test_{test_case.id}",
                "webhook_data": {
                    "contactId": f"test_{test_case.id}",
                    "type": "WhatsApp"
                },
                "extracted_data": {},
                "lead_score": 0
            }
            
            # Process each message
            final_agent = None
            final_score = 0
            
            for i, message in enumerate(test_case.messages):
                logger.info(f"  Message {i+1}: {message}")
                
                # Add user message
                state["messages"].append(HumanMessage(content=message))
                
                # Run workflow
                result = await self.workflow.ainvoke(state)
                
                # Track the execution
                trace.append({
                    "step": i + 1,
                    "message": message,
                    "agent": result.get("current_agent"),
                    "score": result.get("lead_score"),
                    "routing": result.get("next_agent")
                })
                
                # Update state for next iteration
                state = result
                final_agent = result.get("current_agent")
                final_score = result.get("lead_score", 0)
                
                # Log agent response
                if result.get("messages"):
                    last_msg = result["messages"][-1]
                    if isinstance(last_msg, AIMessage):
                        logger.info(f"  Response: {last_msg.content[:100]}...")
            
            # Calculate metrics
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Check routing accuracy
            routing_correct = final_agent == test_case.expected_agent
            if not routing_correct:
                errors.append(f"Expected agent {test_case.expected_agent}, got {final_agent}")
            
            # Check score range
            score_in_range = test_case.expected_score_range[0] <= final_score <= test_case.expected_score_range[1]
            if not score_in_range:
                errors.append(f"Score {final_score} outside expected range {test_case.expected_score_range}")
            
            # Create result
            result = EvalResult(
                test_case_id=test_case.id,
                success=routing_correct and score_in_range,
                actual_agent=final_agent,
                actual_score=final_score,
                messages_exchanged=len(state.get("messages", [])),
                response_time_ms=response_time,
                errors=errors,
                trace=trace
            )
            
            # Calculate metrics
            result.metrics[EvalMetric.ROUTING_ACCURACY] = 1.0 if routing_correct else 0.0
            result.metrics[EvalMetric.TASK_COMPLETION] = 1.0 if result.success else 0.0
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating {test_case.id}: {str(e)}")
            return EvalResult(
                test_case_id=test_case.id,
                success=False,
                actual_agent="error",
                actual_score=0,
                messages_exchanged=0,
                response_time_ms=0,
                errors=[str(e)]
            )
    
    async def evaluate_all(self) -> Dict[str, Any]:
        """Evaluate all test cases"""
        logger.info(f"Starting evaluation of {len(self.test_cases)} test cases")
        
        results = []
        for test_case in self.test_cases:
            result = await self.evaluate_single(test_case)
            results.append(result)
            
        # Calculate aggregate metrics
        total = len(results)
        successful = sum(1 for r in results if r.success)
        
        aggregate_metrics = {
            "total_tests": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "average_response_time_ms": sum(r.response_time_ms for r in results) / total if total > 0 else 0,
            "average_messages": sum(r.messages_exchanged for r in results) / total if total > 0 else 0
        }
        
        # Group by metric
        for metric in EvalMetric:
            scores = [r.metrics.get(metric, 0) for r in results if metric in r.metrics]
            if scores:
                aggregate_metrics[f"average_{metric.value}"] = sum(scores) / len(scores)
        
        return {
            "summary": aggregate_metrics,
            "results": [self._result_to_dict(r) for r in results],
            "timestamp": datetime.now().isoformat()
        }
    
    def _result_to_dict(self, result: EvalResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "test_case_id": result.test_case_id,
            "success": result.success,
            "actual_agent": result.actual_agent,
            "actual_score": result.actual_score,
            "messages_exchanged": result.messages_exchanged,
            "response_time_ms": result.response_time_ms,
            "errors": result.errors,
            "metrics": {k.value: v for k, v in result.metrics.items()},
            "trace": result.trace
        }
    
    async def evaluate_state_simplification(self, workflow) -> Dict[str, Any]:
        """Evaluate state field usage"""
        from app.state.conversation_state import ConversationState
        from app.state.simplified_state import SimplifiedState
        
        # Count fields
        original_fields = len([f for f in dir(ConversationState) if not f.startswith('_')])
        simplified_fields = len([f for f in dir(SimplifiedState) if not f.startswith('_')])
        
        return {
            "original_field_count": original_fields,
            "simplified_field_count": simplified_fields,
            "reduction_percentage": ((original_fields - simplified_fields) / original_fields) * 100,
            "meets_target": simplified_fields <= 15
        }


async def run_evaluation(workflow):
    """Run full evaluation suite"""
    evaluator = MultiAgentEvaluator(workflow)
    
    # Run all tests
    results = await evaluator.evaluate_all()
    
    # Save results
    with open("evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*50)
    print("EVALUATION SUMMARY")
    print("="*50)
    
    summary = results["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']*100:.1f}%")
    print(f"Avg Response Time: {summary['average_response_time_ms']:.0f}ms")
    print(f"Avg Messages: {summary['average_messages']:.1f}")
    
    # Print failed tests
    if summary['failed'] > 0:
        print("\nFAILED TESTS:")
        for result in results["results"]:
            if not result["success"]:
                print(f"- {result['test_case_id']}: {', '.join(result['errors'])}")
    
    return results


# Export
__all__ = [
    "TestCase",
    "EvalResult", 
    "MultiAgentEvaluator",
    "run_evaluation",
    "EvalMetric"
]