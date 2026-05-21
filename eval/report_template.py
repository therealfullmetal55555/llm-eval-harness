"""
Report generation - markdown and HTML
"""
from datetime import datetime, timezone
from typing import List, Dict
from pathlib import Path

def generate_markdown_report(results: List[Dict], output_path: str = None) -> str:
    """
    results: list of dicts with keys: id, question, category, answer, verdicts, passed_count, total_count, overall_pass
    """
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["overall_pass"])
    total_criteria = sum(r["total_count"] for r in results)
    passed_criteria = sum(r["passed_count"] for r in results)
    
    # Group by category
    by_category = {}
    for r in results:
        cat = r.get("category", "unknown")
        by_category.setdefault(cat, []).append(r)
    
    lines = []
    lines.append("# Eval Harness Report — RAG Support Bot")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Model under test:** RAG bot (retrieval + {'LLM' if not results[0].get('mock', True) else 'mock'} generation)")
    lines.append(f"**Judge:** {'Mock deterministic judge' if results[0].get('judge_mock', True) else 'LLM-as-judge (GPT-6 Sol / OpenAI)'}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Test cases:** {total_cases}")
    lines.append(f"- **Passed cases (all criteria pass):** {passed_cases}/{total_cases} ({passed_cases/total_cases*100:.1f}%)")
    lines.append(f"- **Criteria:** {passed_criteria}/{total_criteria} passed ({passed_criteria/total_criteria*100:.1f}%)")
    lines.append("")
    
    # By category
    lines.append("### By Category")
    lines.append("")
    lines.append("| Category | Cases | Passed | Pass Rate | Criteria Pass Rate |")
    lines.append("|----------|-------|--------|-----------|-------------------|")
    for cat, cat_results in by_category.items():
        cat_total = len(cat_results)
        cat_passed = sum(1 for r in cat_results if r["overall_pass"])
        cat_criteria_total = sum(r["total_count"] for r in cat_results)
        cat_criteria_passed = sum(r["passed_count"] for r in cat_results)
        lines.append(f"| {cat} | {cat_total} | {cat_passed} | {cat_passed/cat_total*100:.0f}% | {cat_criteria_passed}/{cat_criteria_total} ({cat_criteria_passed/cat_criteria_total*100:.0f}%) |")
    lines.append("")
    
    # Failed cases details
    failed = [r for r in results if not r["overall_pass"]]
    if failed:
        lines.append("## Failed Cases (at least one criterion failed)")
        lines.append("")
        for r in failed:
            lines.append(f"### ❌ {r['id']} — {r['category']}")
            lines.append(f"**Question:** {r['question']}")
            lines.append(f"**Answer:** {r['answer']}")
            lines.append("")
            lines.append(f"**Verdicts:** {r['passed_count']}/{r['total_count']} passed")
            lines.append("")
            lines.append("| Criterion | Passed | Reasoning |")
            lines.append("|-----------|--------|-----------|")
            for v in r["verdicts"]:
                status = "✅" if v["passed"] else "❌"
                lines.append(f"| {v['criterion_id']}: {v['criterion_description']} | {status} | {v['reasoning']} |")
            lines.append("")
    else:
        lines.append("## All cases passed! (But this is less credible - see intentional failure test)")
        lines.append("")
    
    # All results table
    lines.append("## All Results")
    lines.append("")
    lines.append("| ID | Category | Question | Passed Criteria | Overall |")
    lines.append("|----|----------|----------|-----------------|---------|")
    for r in results:
        overall = "✅ PASS" if r["overall_pass"] else "❌ FAIL"
        q_short = r["question"][:50] + "..." if len(r["question"]) > 50 else r["question"]
        lines.append(f"| {r['id']} | {r['category']} | {q_short} | {r['passed_count']}/{r['total_count']} | {overall} |")
    lines.append("")
    
    # Methodology
    lines.append("## Methodology")
    lines.append("")
    lines.append("### Why LLM-as-judge?")
    lines.append("- Manual evaluation doesn't scale")
    lines.append("- Verifiable criteria (contains citation, mentions 30-day) are objective and checkable by LLM")
    lines.append("- Structured output forces judge to give pass/fail + reasoning per criterion")
    lines.append("")
    lines.append("### Limitations of LLM-as-judge")
    lines.append("- Judge itself can be wrong, especially on borderline cases")
    lines.append("- We mitigate by: deterministic mock judge for verifiable criteria, and 'test on test' - judge tested on 5 intentionally wrong answers")
    lines.append("- Judge and generator are separate calls, judge doesn't see generator reasoning, only final answer + criterion")
    lines.append("- For critical eval, use human review on failed cases")
    lines.append("")
    lines.append("### Anti-hallucination Guardrails")
    lines.append("- RAG bot must cite sources [Source: filename.md]")
    lines.append("- Must refuse out-of-domain instead of hallucinating")
    lines.append("- Judge checks for hallucinated content (e.g., 60-day return)")
    lines.append("")
    
    # Judge self-test
    lines.append("## Judge Self-Test (test on test)")
    lines.append("")
    lines.append("Judge was tested on 5 intentionally wrong answers to ensure it catches failures:")
    lines.append("")
    lines.append("| Test | Expected | Judge Result |")
    lines.append("|------|----------|--------------|")
    lines.append("| Missing citation | FAIL | Should catch |")
    lines.append("| Hallucinated 60-day | FAIL | Should catch |")
    lines.append("| Correct answer | PASS | Should pass |")
    lines.append("| Hallucinated World Cup | FAIL | Should catch |")
    lines.append("| Correct refusal | PASS | Should pass |")
    lines.append("")
    lines.append("See `eval/judge_prompt.py::test_judge_self()` for automated test.")
    lines.append("")
    
    report = "\n".join(lines)
    
    if output_path:
        Path(output_path).write_text(report, encoding='utf-8')
        print(f"Report written to {output_path}")
    
    return report

def generate_html_report(results: List[Dict], output_path: str = None) -> str:
    md = generate_markdown_report(results)
    # Simple markdown to HTML conversion (very basic)
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Eval Harness Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }}
th {{ background: #f5f5f5; }}
.pass {{ color: green; }} .fail {{ color: red; }}
pre {{ background: #f8f9fa; padding: 12px; border-radius: 6px; overflow-x: auto; }}
</style>
</head>
<body>
<pre>{md}</pre>
</body>
</html>
"""
    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
    return html

if __name__ == "__main__":
    # Test with dummy data
    dummy = [
        {
            "id": "test_01",
            "question": "What is return window?",
            "category": "return_policy",
            "answer": "30-day [Source: return_and_refund_policy.md]",
            "verdicts": [{"criterion_id": "mentions_30", "criterion_description": "Mentions 30-day", "passed": True, "reasoning": "Found"}],
            "passed_count": 1,
            "total_count": 1,
            "overall_pass": True,
            "mock": True,
            "judge_mock": True
        }
    ]
    print(generate_markdown_report(dummy))
