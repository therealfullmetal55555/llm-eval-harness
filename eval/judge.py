"""
Judge - evaluates bot answer against criteria
Supports real LLM judge and mock deterministic judge
"""
import json
import logging
from typing import Dict, List
from pydantic import BaseModel, Field

from .config import OPENAI_API_KEY, JUDGE_MODEL, JUDGE_BASE_URL, USE_MOCK_JUDGE
from .judge_prompt import JUDGE_SYSTEM_PROMPT, build_judge_user_prompt, mock_judge_evaluate

logger = logging.getLogger(__name__)

class CriterionVerdict(BaseModel):
    criterion_id: str = Field(description="ID of criterion")
    passed: bool = Field(description="Whether criterion passed")
    reasoning: str = Field(description="Brief reasoning")
    criterion_description: str = Field(default="", description="Original criterion description")
    criterion_type: str = Field(default="", description="Type of check")
    criterion_value: str = Field(default="", description="Value to check")

class JudgeResult(BaseModel):
    question: str
    answer: str
    criterion_id: str
    passed: bool
    reasoning: str

def llm_judge(question: str, answer: str, criterion: dict) -> CriterionVerdict:
    """
    Calls LLM to judge if answer passes criterion
    """
    if USE_MOCK_JUDGE:
        passed, reasoning = mock_judge_evaluate(answer, criterion)
        return CriterionVerdict(
            criterion_id=criterion["id"],
            passed=passed,
            reasoning=reasoning,
            criterion_description=criterion.get("description", ""),
            criterion_type=criterion.get("type", ""),
            criterion_value=str(criterion.get("value", ""))
        )
    
    try:
        from openai import OpenAI
        client_kwargs = {}
        if JUDGE_BASE_URL:
            client_kwargs["base_url"] = JUDGE_BASE_URL
        client_kwargs["api_key"] = OPENAI_API_KEY
        client = OpenAI(**client_kwargs)
        
        user_prompt = build_judge_user_prompt(question, answer, criterion)
        
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # Expect {passed: bool, reasoning: str}
        passed = data.get("passed", False)
        reasoning = data.get("reasoning", "No reasoning provided")
        
        return CriterionVerdict(
            criterion_id=criterion["id"],
            passed=bool(passed),
            reasoning=reasoning,
            criterion_description=criterion.get("description", ""),
            criterion_type=criterion.get("type", ""),
            criterion_value=str(criterion.get("value", ""))
        )
    
    except Exception as e:
        logger.error(f"LLM judge failed, fallback to mock: {e}")
        passed, reasoning = mock_judge_evaluate(answer, criterion)
        return CriterionVerdict(
            criterion_id=criterion["id"],
            passed=passed,
            reasoning=f"[FALLBACK MOCK] {reasoning} (LLM judge error: {e})",
            criterion_description=criterion.get("description", ""),
            criterion_type=criterion.get("type", ""),
            criterion_value=str(criterion.get("value", ""))
        )

def evaluate_answer(question: str, answer: str, criteria: List[dict]) -> List[CriterionVerdict]:
    """
    Evaluate answer against all criteria for a test case
    Returns list of verdicts per criterion
    """
    verdicts = []
    for criterion in criteria:
        verdict = llm_judge(question, answer, criterion)
        verdicts.append(verdict)
    return verdicts

if __name__ == "__main__":
    # Test judge
    from .judge_prompt import test_judge_self
    test_judge_self()
    
    # Test one evaluation
    q = "What is your return window?"
    a = "We offer 30-day return window [Source: return_and_refund_policy.md]"
    criteria = [
        {"id": "mentions_30_days", "description": "Mentions 30-day", "type": "contains", "value": "30-day"},
        {"id": "cites_return_policy", "description": "Contains citation", "type": "contains", "value": "[Source: return_and_refund_policy.md]"}
    ]
    verdicts = evaluate_answer(q, a, criteria)
    for v in verdicts:
        print(f"{v.criterion_id}: {v.passed} - {v.reasoning}")
