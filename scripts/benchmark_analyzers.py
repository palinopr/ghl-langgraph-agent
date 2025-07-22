"""
Benchmark regex-based vs LLM-based intelligence analyzers
"""
import asyncio
import time
from typing import List, Dict, Any
from app.intelligence.analyzer import IntelligenceAnalyzer as RegexAnalyzer
from app.intelligence.simple_analyzer import SimpleIntelligenceAnalyzer as LLMAnalyzer
from app.utils.simple_logger import get_logger

logger = get_logger("benchmark")

# Real production examples (anonymized)
TEST_CASES = [
    # 1. Simple introduction
    {
        "message": "Hola soy Maria y tengo un restaurante",
        "expected": {
            "name": "Maria",
            "business_type": "restaurante",
            "budget": None,
            "goal": None
        }
    },
    # 2. Typo in business
    {
        "message": "tengo un reaturante en el centro",
        "expected": {
            "name": None,
            "business_type": "restaurante",
            "budget": None,
            "goal": None
        }
    },
    # 3. Budget mention
    {
        "message": "mi presupuesto es como unos 300 al mes",
        "expected": {
            "name": None,
            "business_type": None,
            "budget": "300",
            "goal": None
        }
    },
    # 4. Complex sentence
    {
        "message": "Soy Carlos, manejo una barbería y estoy perdiendo clientes por no tener sistema de citas",
        "expected": {
            "name": "Carlos",
            "business_type": "barbería",
            "budget": None,
            "goal": "perdiendo clientes por no tener sistema de citas"
        }
    },
    # 5. Variation in business description
    {
        "message": "trabajo en un gym pequeño",
        "expected": {
            "name": None,
            "business_type": "gym",
            "budget": None,
            "goal": None
        }
    },
    # 6. Multiple pieces of info
    {
        "message": "Me llamo Ana, tengo una tienda de ropa y mi presupuesto es de 400",
        "expected": {
            "name": "Ana",
            "business_type": "tienda",
            "budget": "400",
            "goal": None
        }
    },
    # 7. Business with context
    {
        "message": "tengo un negocio de comida rapida",
        "expected": {
            "name": None,
            "business_type": "restaurante",  # Should understand food business
            "budget": None,
            "goal": None
        }
    },
    # 8. Just confirmation
    {
        "message": "si claro",
        "expected": {
            "name": None,
            "business_type": None,
            "budget": None,
            "goal": None
        }
    },
    # 9. Budget range
    {
        "message": "puedo invertir entre 300 y 500 dolares",
        "expected": {
            "name": None,
            "business_type": None,
            "budget": "300-500",
            "goal": None
        }
    },
    # 10. Problem statement
    {
        "message": "necesito automatizar las respuestas en whatsapp",
        "expected": {
            "name": None,
            "business_type": None,
            "budget": None,
            "goal": "automatizar las respuestas en whatsapp"
        }
    }
]


def calculate_accuracy(extracted: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """Calculate accuracy of extraction"""
    correct = 0
    total = 0
    
    for key in expected:
        total += 1
        if extracted.get(key) == expected[key]:
            correct += 1
        elif extracted.get(key) and expected[key]:
            # Partial match for similar values
            if isinstance(extracted[key], str) and isinstance(expected[key], str):
                if extracted[key].lower() in expected[key].lower() or \
                   expected[key].lower() in extracted[key].lower():
                    correct += 0.5
    
    return (correct / total) if total > 0 else 0


async def benchmark_analyzer(analyzer_name: str, analyzer: Any, test_cases: List[Dict]) -> Dict[str, Any]:
    """Benchmark a single analyzer"""
    logger.info(f"\n{'='*50}")
    logger.info(f"Benchmarking {analyzer_name}")
    logger.info(f"{'='*50}")
    
    results = []
    total_time = 0
    
    for i, test in enumerate(test_cases):
        # Create minimal state with proper message objects
        from langchain_core.messages import HumanMessage
        state = {
            "messages": [HumanMessage(content=test["message"])],
            "extracted_data": {},
            "lead_score": 0,
            "score_history": []
        }
        
        # Time the extraction
        start_time = time.time()
        
        try:
            result_state = await analyzer.analyze(state)
            extracted = result_state.get("extracted_data", {})
        except Exception as e:
            logger.error(f"Error in {analyzer_name}: {e}")
            extracted = {}
        
        elapsed = time.time() - start_time
        total_time += elapsed
        
        # Calculate accuracy
        accuracy = calculate_accuracy(extracted, test["expected"])
        
        # Log results
        logger.info(f"\nTest {i+1}: \"{test['message']}\"")
        logger.info(f"Expected: {test['expected']}")
        logger.info(f"Extracted: {extracted}")
        logger.info(f"Accuracy: {accuracy:.1%}")
        logger.info(f"Time: {elapsed:.3f}s")
        
        results.append({
            "test": i + 1,
            "accuracy": accuracy,
            "time": elapsed,
            "extracted": extracted,
            "expected": test["expected"]
        })
    
    # Calculate summary stats
    avg_accuracy = sum(r["accuracy"] for r in results) / len(results)
    avg_time = total_time / len(results)
    
    return {
        "analyzer": analyzer_name,
        "results": results,
        "avg_accuracy": avg_accuracy,
        "total_time": total_time,
        "avg_time": avg_time
    }


async def main():
    """Run the benchmark comparison"""
    logger.info("Starting Intelligence Analyzer Benchmark")
    
    # Initialize analyzers
    regex_analyzer = RegexAnalyzer()
    llm_analyzer = LLMAnalyzer()
    
    # Run benchmarks
    regex_results = await benchmark_analyzer("Regex-based Analyzer", regex_analyzer, TEST_CASES)
    llm_results = await benchmark_analyzer("LLM-based Analyzer", llm_analyzer, TEST_CASES)
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("BENCHMARK SUMMARY")
    logger.info(f"{'='*50}")
    
    logger.info(f"\nRegex-based Analyzer:")
    logger.info(f"  Average Accuracy: {regex_results['avg_accuracy']:.1%}")
    logger.info(f"  Average Time: {regex_results['avg_time']:.3f}s")
    logger.info(f"  Total Time: {regex_results['total_time']:.3f}s")
    
    logger.info(f"\nLLM-based Analyzer:")
    logger.info(f"  Average Accuracy: {llm_results['avg_accuracy']:.1%}")
    logger.info(f"  Average Time: {llm_results['avg_time']:.3f}s")
    logger.info(f"  Total Time: {llm_results['total_time']:.3f}s")
    
    # Determine winner
    if llm_results['avg_accuracy'] >= 0.9:
        logger.info(f"\n✅ LLM-based analyzer achieves {llm_results['avg_accuracy']:.1%} accuracy!")
        logger.info("Recommendation: Replace regex analyzer with LLM-based approach")
    else:
        logger.info(f"\n❌ LLM-based analyzer only achieves {llm_results['avg_accuracy']:.1%} accuracy")
        logger.info("Recommendation: Keep regex analyzer for now")
    
    return regex_results, llm_results


if __name__ == "__main__":
    asyncio.run(main())