"""
Judge prompt - separated from code for easy iteration
This is the prompt for LLM-as-judge that evaluates RAG bot answers
"""

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator for a RAG support bot.

Your task: Given a question, the bot's answer, and a specific criterion, decide if the answer PASSES or FAILS that criterion.

CRITICAL RULES:
- Be objective and strict, but fair
- Criterion is verifiable: check if answer contains / does not contain specific text, or correctly refuses
- For "contains" criteria: answer must have the exact substring or semantic equivalent
- For "not_contains": answer must NOT have that substring
- For refusal: answer should say it doesn't have info, out of scope, cannot answer, etc.
- Provide brief reasoning (1-2 sentences)
- Do NOT be fooled by plausible but incorrect answers

Return JSON with:
- passed: bool
- reasoning: str (why pass/fail)

Examples:

Criterion: "Answer mentions 30-day return window" / contains "30-day"
Answer: "We offer 30-day return window [Source: return_and_refund_policy.md]"
-> passed=true, reasoning="Mentions 30-day explicitly"

Criterion: "Answer contains citation [Source: return_and_refund_policy.md]" / contains "[Source: return_and_refund_policy.md]"
Answer: "We have 30-day returns"
-> passed=false, reasoning="Mentions 30-day but no citation"

Criterion: "Correctly refuses out-of-domain" / contains_any ["don't have information", "out of scope"]
Answer: "Argentina won World Cup 2022"
-> passed=false, reasoning="Hallucinated answer instead of refusing"

Criterion: "Does NOT mention 60-day return" / not_contains "60-day"
Answer: "We offer 60-day returns"
-> passed=false, reasoning="Mentions 60-day which is incorrect"
"""

def build_judge_user_prompt(question: str, answer: str, criterion: dict) -> str:
    return f"""
Question: {question}

Bot Answer: {answer}

Criterion to check:
ID: {criterion['id']}
Description: {criterion['description']}
Type: {criterion['type']}
Value: {criterion['value']}

Does the bot answer PASS this criterion? Return JSON.
"""

# For mock judge - rule-based evaluation that is deterministic and testable
def mock_judge_evaluate(answer: str, criterion: dict) -> tuple[bool, str]:
    """
    Deterministic mock judge that checks criteria via string matching
    This is actually MORE reliable than LLM judge for verifiable criteria,
    and useful for testing the eval harness itself.
    """
    c_type = criterion.get("type")
    c_value = criterion.get("value")
    c_desc = criterion.get("description", "")

    answer_lower = answer.lower()
    
    if c_type == "contains":
        passed = c_value.lower() in answer_lower if isinstance(c_value, str) else False
        reasoning = f"{'Found' if passed else 'Did not find'} '{c_value}' in answer" if passed else f"Expected '{c_value}' not found in answer"
        return passed, reasoning
    
    elif c_type == "not_contains":
        passed = c_value.lower() not in answer_lower if isinstance(c_value, str) else True
        reasoning = f"Correctly does not contain '{c_value}'" if passed else f"Should not contain '{c_value}' but found it"
        return passed, reasoning
    
    elif c_type == "contains_any":
        # c_value is list
        if isinstance(c_value, list):
            found = [v for v in c_value if v.lower() in answer_lower]
            passed = len(found) > 0
            reasoning = f"Found one of {c_value}: {found[0] if found else 'none'}" if passed else f"None of {c_value} found"
            return passed, reasoning
        else:
            passed = c_value.lower() in answer_lower
            return passed, f"Found '{c_value}'" if passed else f"Not found '{c_value}'"
    
    elif c_type == "contains_all":
        if isinstance(c_value, list):
            missing = [v for v in c_value if v.lower() not in answer_lower]
            passed = len(missing) == 0
            reasoning = f"All of {c_value} found" if passed else f"Missing: {missing}"
            return passed, reasoning
        else:
            passed = c_value.lower() in answer_lower
            return passed, f"Found '{c_value}'" if passed else f"Not found"
    
    else:
        # Unknown type - fail safe
        return False, f"Unknown criterion type {c_type}"

# Test for judge itself - "test on test" - intentionally wrong answers should be caught
JUDGE_SELF_TESTS = [
    {
        "name": "Should catch missing citation",
        "answer": "We have 30-day returns",
        "criterion": {"id": "cites_return_policy", "description": "Contains citation", "type": "contains", "value": "[Source: return_and_refund_policy.md]"},
        "expected_pass": False
    },
    {
        "name": "Should catch hallucinated 60-day",
        "answer": "We offer 60-day returns [Source: return_and_refund_policy.md]",
        "criterion": {"id": "no_hallucinated_60", "description": "Does NOT mention 60-day", "type": "not_contains", "value": "60-day"},
        "expected_pass": False
    },
    {
        "name": "Should pass correct answer",
        "answer": "We offer 30-day return window [Source: return_and_refund_policy.md]",
        "criterion": {"id": "mentions_30_days", "description": "Mentions 30-day", "type": "contains", "value": "30-day"},
        "expected_pass": True
    },
    {
        "name": "Should catch hallucinated World Cup answer",
        "answer": "Argentina won World Cup 2022",
        "criterion": {"id": "correctly_refuses", "description": "Refuses out-of-domain", "type": "contains_any", "value": ["don't have information", "out of scope", "cannot answer"]},
        "expected_pass": False
    },
    {
        "name": "Should pass correct refusal",
        "answer": "I don't have information about World Cup, my knowledge base is about products and policies. This is out of scope.",
        "criterion": {"id": "correctly_refuses", "description": "Refuses out-of-domain", "type": "contains_any", "value": ["don't have information", "out of scope", "cannot answer"]},
        "expected_pass": True
    }
]

def test_judge_self():
    print("=== Testing judge on intentionally wrong answers (test on test) ===")
    passed = 0
    for test in JUDGE_SELF_TESTS:
        actual_pass, reasoning = mock_judge_evaluate(test["answer"], test["criterion"])
        expected = test["expected_pass"]
        status = "✅" if actual_pass == expected else "❌"
        if actual_pass == expected:
            passed += 1
        print(f"{status} {test['name']}: expected {expected}, got {actual_pass} - {reasoning}")
    print(f"\nJudge self-test: {passed}/{len(JUDGE_SELF_TESTS)} passed")
    return passed == len(JUDGE_SELF_TESTS)
