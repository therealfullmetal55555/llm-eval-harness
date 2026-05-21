"""
Main eval harness runner
- Loads test cases from YAML
- Calls RAG bot (real, not mock) for each question
- Calls judge (LLM or mock) for each criterion
- Generates report
"""
import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime, timezone

# Ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.config import TEST_CASES_PATH, USE_MOCK_LLM, USE_MOCK_JUDGE
from eval.rag_bot import answer_question
from eval.judge import evaluate_answer
from eval.judge_prompt import test_judge_self
from eval.report_template import generate_markdown_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_test_cases(path: Path = TEST_CASES_PATH):
    with open(path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    cases = data.get("test_cases", [])
    logger.info(f"Loaded {len(cases)} test cases from {path}")
    return cases

def run_eval(test_cases=None, output_report_path: str = None):
    if test_cases is None:
        test_cases = load_test_cases()

    # First, test judge itself (test on test)
    print("\n=== Judge Self-Test (test on test) ===")
    judge_self_ok = test_judge_self()
    print(f"Judge self-test {'PASSED' if judge_self_ok else 'FAILED'}\n")

    results = []
    
    for idx, case in enumerate(test_cases, 1):
        case_id = case["id"]
        question = case["question"]
        category = case.get("category", "unknown")
        criteria = case.get("criteria", [])
        
        print(f"\n[{idx}/{len(test_cases)}] Running {case_id} ({category}): {question[:60]}...")
        
        # 1. Call RAG bot (real)
        try:
            bot_result = answer_question(question)
            answer = bot_result["answer"]
            print(f"  Bot answer: {answer[:120]}...")
            print(f"  Retrieved: {bot_result['retrieved_docs']}")
        except Exception as e:
            logger.error(f"Bot failed for {case_id}: {e}")
            answer = f"ERROR: Bot failed - {e}"
            bot_result = {"answer": answer, "retrieved_docs": []}
        
        # 2. Call judge for each criterion
        try:
            verdicts = evaluate_answer(question, answer, criteria)
            passed_count = sum(1 for v in verdicts if v.passed)
            total_count = len(verdicts)
            overall_pass = passed_count == total_count
            
            print(f"  Judge: {passed_count}/{total_count} criteria passed, overall={'PASS' if overall_pass else 'FAIL'}")
            for v in verdicts:
                status = "✅" if v.passed else "❌"
                print(f"    {status} {v.criterion_id}: {v.reasoning}")
            
        except Exception as e:
            logger.error(f"Judge failed for {case_id}: {e}")
            verdicts = []
            passed_count = 0
            total_count = len(criteria)
            overall_pass = False
        
        results.append({
            "id": case_id,
            "question": question,
            "category": category,
            "answer": answer,
            "retrieved_docs": bot_result.get("retrieved_docs", []),
            "verdicts": [{"criterion_id": v.criterion_id, "criterion_description": v.criterion_description, 
                          "passed": v.passed, "reasoning": v.reasoning, 
                          "criterion_type": v.criterion_type, "criterion_value": v.criterion_value} for v in verdicts],
            "passed_count": passed_count,
            "total_count": total_count,
            "overall_pass": overall_pass,
            "mock": USE_MOCK_LLM,
            "judge_mock": USE_MOCK_JUDGE
        })
    
    # Generate report
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = Path(__file__).parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)
    
    report_path = report_dir / f"eval_report_{timestamp}.md"
    markdown_report = generate_markdown_report(results, output_path=str(report_path))
    
    # Also latest
    latest_path = report_dir / "latest_report.md"
    latest_path.write_text(markdown_report, encoding='utf-8')
    
    print("\n\n=== EVAL SUMMARY ===")
    total = len(results)
    passed = sum(1 for r in results if r["overall_pass"])
    total_criteria = sum(r["total_count"] for r in results)
    passed_criteria = sum(r["passed_count"] for r in results)
    
    print(f"Test cases: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"Criteria: {passed_criteria}/{total_criteria} passed ({passed_criteria/total_criteria*100:.1f}%)")
    print(f"Report: {report_path}")
    print(f"Latest: {latest_path}")
    
    # Show at least one real failure for credibility
    failed = [r for r in results if not r["overall_pass"]]
    if failed:
        print(f"\n❌ Failed cases ({len(failed)}):")
        for f in failed:
            print(f"  - {f['id']}: {f['question'][:60]}... - {f['passed_count']}/{f['total_count']}")
    else:
        print("\n⚠️ All cases passed - consider adding a tricky case to show real failure for portfolio credibility")
    
    return results, str(report_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run eval harness")
    parser.add_argument("--cases", type=str, default=str(TEST_CASES_PATH), help="Path to test_cases.yaml")
    parser.add_argument("--output", type=str, default=None, help="Output report path")
    args = parser.parse_args()
    
    test_cases = load_test_cases(Path(args.cases))
    run_eval(test_cases, output_report_path=args.output)
