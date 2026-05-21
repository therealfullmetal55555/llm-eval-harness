import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

JUDGE_MODEL = os.getenv("JUDGE_MODEL", OPENAI_MODEL)
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", OPENAI_BASE_URL)

KB_PATH = BASE_DIR / os.getenv("EVAL_KB_PATH", "kb/")
TEST_CASES_PATH = BASE_DIR / os.getenv("EVAL_TEST_CASES", "eval/test_cases.yaml")

USE_MOCK_LLM = not bool(OPENAI_API_KEY)
USE_MOCK_JUDGE = not bool(OPENAI_API_KEY)  # if no API key, use mock judge
