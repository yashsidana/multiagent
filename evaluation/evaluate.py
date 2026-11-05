import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from src.agents.graph import run_copilot_workflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluator")

EVAL_DIR = Path(__file__).resolve().parent
TEST_DATASET_PATH = EVAL_DIR / "test_dataset.json"


def run_evaluation() -> Dict[str, Any]:
    """
    Executes benchmark evaluation across test dataset questions.
    Measures Routing Accuracy, Retrieval Hit Rate, Latency, and Refusal behavior.
    """
    if not TEST_DATASET_PATH.exists():
        logger.error("Dataset not found at %s", TEST_DATASET_PATH)
        return {}

    with open(TEST_DATASET_PATH, "r", encoding="utf-8") as f:
        test_cases: List[Dict[str, Any]] = json.load(f)

    total_cases = len(test_cases)
    route_correct = 0
    retrieval_hits = 0
    retrieval_tests = 0
    sql_executions = 0
    sql_successes = 0
    refusal_successes = 0
    refusal_tests = 0
    total_latency = 0.0
    total_tokens = 0

    print("\n" + "=" * 80)
    print(f"🚀 STARTING EVALUATION BENCHMARK ({total_cases} Test Cases)")
    print("=" * 80)

    for i, item in enumerate(test_cases, 1):
        q = item["question"]
        expected_route = item["expected_route"]
        expected_source = item.get("expected_source")
        should_refuse = item.get("should_refuse", False)

        t0 = time.time()
        res = run_copilot_workflow(q)
        duration = time.time() - t0

        actual_route = res.get("route", "")
        tokens = res.get("tokens_used", 0)
        total_latency += duration
        total_tokens += tokens

        # 1. Routing check
        is_route_correct = (actual_route == expected_route) or (
            expected_route == "hybrid" and actual_route in ["sql", "rag", "hybrid"]
        )
        if is_route_correct:
            route_correct += 1

        # 2. Retrieval Hit Rate check
        if expected_source:
            retrieval_tests += 1
            retrieved_sources = [s["source"] for s in res.get("rag_sources", [])]
            if expected_source in retrieved_sources:
                retrieval_hits += 1

        # 3. SQL check
        if actual_route in ["sql", "hybrid"]:
            sql_executions += 1
            if res.get("sql_results") is not None and not res.get("sql_error"):
                sql_successes += 1

        # 4. Refusal check for unanswerable questions
        if should_refuse:
            refusal_tests += 1
            ans = res.get("final_answer", "").lower()
            if any(k in ans for k in ["not contain", "do not know", "no information", "cannot find", "not available"]):
                refusal_successes += 1

        print(f"[{i}/{total_cases}] Question: {q[:55]}...")
        print(f"    Expected: {expected_route.upper():<6} | Actual: {actual_route.upper():<6} | Latency: {duration:.2f}s | Tokens: {tokens}")

    # Compute Metrics
    routing_acc = (route_correct / total_cases) * 100 if total_cases else 0.0
    retrieval_hit_rate = (retrieval_hits / retrieval_tests) * 100 if retrieval_tests else 0.0
    sql_accuracy = (sql_successes / sql_executions) * 100 if sql_executions else 0.0
    refusal_acc = (refusal_successes / refusal_tests) * 100 if refusal_tests else 0.0
    avg_latency = total_latency / total_cases if total_cases else 0.0
    avg_tokens = total_tokens / total_cases if total_cases else 0.0

    print("\n" + "=" * 80)
    print("📊 BENCHMARK EVALUATION SUMMARY")
    print("=" * 80)
    print(f"  • Total Questions Evaluated:    {total_cases}")
    print(f"  • Router Classification Accuracy: {routing_acc:.1f}%")
    print(f"  • Document Retrieval Hit Rate:  {retrieval_hit_rate:.1f}% ({retrieval_hits}/{retrieval_tests})")
    print(f"  • SQL Execution Success Rate:   {sql_accuracy:.1f}% ({sql_successes}/{sql_executions})")
    print(f"  • Unanswerable Refusal Rate:    {refusal_acc:.1f}%")
    print(f"  • Average Latency per Query:    {avg_latency:.2f} seconds")
    print(f"  • Average Tokens per Query:     {avg_tokens:.0f} tokens")
    print("=" * 80 + "\n")

    return {
        "total_cases": total_cases,
        "routing_accuracy": routing_acc,
        "retrieval_hit_rate": retrieval_hit_rate,
        "sql_accuracy": sql_accuracy,
        "avg_latency": avg_latency,
        "avg_tokens": avg_tokens
    }


if __name__ == "__main__":
    run_evaluation()

