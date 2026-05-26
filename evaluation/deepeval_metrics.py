"""
Layer 2: DeepEval-backed metrics using Azure OpenAI.

Each metric is a focused, independent LLM call with a specific rubric.
All three run with temperature=0 to minimise run-to-run variance.

Metrics:
  summarization — does the documentation cover the key facts in the source code?
  faithfulness  — does the documentation hallucinate facts absent from the source?
  clarity       — is the documentation clear, structured, and unambiguous? (GEval)

Azure OpenAI is wired in via a custom DeepEvalBaseLLM subclass that reuses the
same endpoint/key configuration from config.py — no separate env vars needed.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


# ── Azure OpenAI adapter for DeepEval ─────────────────────────────────────────

class _AzureDeepEvalModel:
    """
    Wraps our AzureChatOpenAI client so DeepEval metrics use the same
    endpoint and deployment as the rest of the pipeline.
    """

    def __init__(self):
        try:
            from deepeval.models.base_model import DeepEvalBaseLLM
            self._base_cls = DeepEvalBaseLLM
        except ImportError:
            self._base_cls = None
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from utils.llm_client import get_llm
            self._llm = get_llm(temperature=0.0, max_tokens=2_048)
        return self._llm

    def generate(self, prompt: str, *args, **kwargs) -> str:
        from langchain_core.messages import HumanMessage
        response = self._get_llm().invoke([HumanMessage(content=prompt)])
        return response.content

    async def a_generate(self, prompt: str, *args, **kwargs) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return "azure-openai"


def _build_deepeval_model():
    """
    Build a DeepEval-compatible model object.
    Attempts to subclass DeepEvalBaseLLM; falls back to a duck-typed wrapper
    if the deepeval version changes the base class interface.
    """
    try:
        from deepeval.models.base_model import DeepEvalBaseLLM

        class _Model(DeepEvalBaseLLM):
            def load_model(self):
                from utils.llm_client import get_llm
                return get_llm(temperature=0.0, max_tokens=2_048)

            def generate(self, prompt: str, *args, **kwargs) -> str:
                from langchain_core.messages import HumanMessage
                response = self.load_model().invoke([HumanMessage(content=prompt)])
                return response.content

            async def a_generate(self, prompt: str, *args, **kwargs) -> str:
                return self.generate(prompt)

            def get_model_name(self) -> str:
                return "azure-openai"

        return _Model()
    except Exception:
        return _AzureDeepEvalModel()


_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = _build_deepeval_model()
    return _MODEL


# ── Individual metric runners ─────────────────────────────────────────────────

def run_summarization(source_code_snippet: str, documentation: dict) -> Dict:
    """
    SummarizationMetric: does the documentation cover the key points from the source?
    Score 0-1 (higher = better coverage of source facts).
    """
    try:
        from deepeval.metrics import SummarizationMetric
        from deepeval.test_case import LLMTestCase

        doc_text  = json.dumps(documentation, indent=2)[:4_000]
        src_text  = source_code_snippet[:3_000]

        test_case = LLMTestCase(input=src_text, actual_output=doc_text)
        metric    = SummarizationMetric(
            threshold=0.5,
            model=_get_model(),
            verbose_mode=False,
        )
        metric.measure(test_case)
        return {
            "score":  round(float(metric.score), 3),
            "reason": getattr(metric, "reason", "") or "",
            "passed": bool(metric.is_successful()),
        }
    except Exception as exc:
        logger.warning("SummarizationMetric failed: %s", exc)
        return {"score": 0.5, "reason": f"metric unavailable: {exc}", "passed": False}


def run_hallucination(source_code_snippet: str, documentation: dict) -> Dict:
    """
    HallucinationMetric: does the documentation invent facts absent from source?
    DeepEval score=0 means no hallucination; we invert to faithfulness (higher=better).
    """
    try:
        from deepeval.metrics import HallucinationMetric
        from deepeval.test_case import LLMTestCase

        doc_text  = json.dumps(documentation, indent=2)[:4_000]
        src_text  = source_code_snippet[:3_000]

        test_case = LLMTestCase(
            input="Evaluate this documentation for hallucinated facts.",
            actual_output=doc_text,
            context=[src_text],
        )
        metric = HallucinationMetric(
            threshold=0.5,
            model=_get_model(),
            verbose_mode=False,
        )
        metric.measure(test_case)
        hallucination_rate = round(float(metric.score), 3)
        faithfulness       = round(1.0 - hallucination_rate, 3)
        return {
            "score":             faithfulness,       # higher = more faithful
            "hallucination_rate": hallucination_rate,
            "reason":            getattr(metric, "reason", "") or "",
            "passed":            hallucination_rate <= 0.5,
        }
    except Exception as exc:
        logger.warning("HallucinationMetric failed: %s", exc)
        return {"score": 0.5, "hallucination_rate": 0.5, "reason": f"metric unavailable: {exc}", "passed": False}


def run_clarity(documentation: dict) -> Dict:
    """
    GEval (clarity): is the documentation clear, structured, and unambiguous?
    Score 0-1 (higher = clearer documentation).
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCase

        # SingleTurnParams is the current name; LLMTestCaseParams is the legacy alias
        try:
            from deepeval.test_case import SingleTurnParams as _Params
        except ImportError:
            from deepeval.test_case import LLMTestCaseParams as _Params  # type: ignore[no-redef]

        doc_text  = json.dumps(documentation, indent=2)[:4_000]
        test_case = LLMTestCase(
            input="Assess the clarity and structure of this technical documentation.",
            actual_output=doc_text,
        )
        metric = GEval(
            name="DocumentationClarity",
            criteria=(
                "The documentation is clear, unambiguous, and well-structured. "
                "Each module's business logic is explained in plain English that "
                "a developer unfamiliar with the original codebase could understand. "
                "Business rules are concrete, specific, and actionable — not vague. "
                "Data model descriptions include field-level explanations."
            ),
            evaluation_params=[_Params.ACTUAL_OUTPUT],
            model=_get_model(),
            verbose_mode=False,
        )
        metric.measure(test_case)
        return {
            "score":  round(float(metric.score), 3),
            "reason": getattr(metric, "reason", "") or "",
            "passed": bool(metric.is_successful()),
        }
    except Exception as exc:
        logger.warning("GEval (clarity) failed: %s", exc)
        return {"score": 0.5, "reason": f"metric unavailable: {exc}", "passed": False}


def run_all(source_code_snippet: str, documentation: dict) -> Dict:
    """Run all three DeepEval metrics and return combined results."""
    return {
        "summarization": run_summarization(source_code_snippet, documentation),
        "faithfulness":  run_hallucination(source_code_snippet, documentation),
        "clarity":       run_clarity(documentation),
    }
