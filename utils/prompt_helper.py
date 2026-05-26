"""
PromptHelper — centralised prompt manager.

Each agent has a matching prompt module under prompts/<agent_name>_prompts.py
that must define:
  SYSTEM          — system prompt template (may contain {placeholder} syntax)
  USER_TEMPLATE   — user message template  (must contain {placeholder} syntax)

Optional:
  SYSTEM_<VARIANT>  — alternate system prompt selected by `system_variant`
                      e.g. SYSTEM_RETRY in documenter_prompts.py

Usage examples
--------------
# Simple single-call agent
ph = PromptHelper("code_splitter")
result = ph.invoke_and_parse(source_code=raw_java)

# Agent with an alternate system variant (retry pass)
ph = PromptHelper("documenter")
result = ph.invoke_and_parse(
    system_variant="retry",
    system_kwargs={"feedback": feedback_text},
    modules_json=json.dumps(summaries, indent=2),
)

# Agent that needs the threshold injected into the system prompt
ph = PromptHelper("auditor")
result = ph.invoke_and_parse(
    system_kwargs={"threshold": 70.0},
    module_count=len(modules),
    module_names_json=json.dumps(names),
    doc_count=len(docs),
    documented_names_json=json.dumps(doc_names),
    documentation_json=doc_str,
)
"""

import importlib
from typing import Any, Dict, List, Optional, Union

from utils.llm_client import call_llm, parse_json_from_llm


class PromptHelper:
    def __init__(self, agent_name: str) -> None:
        self._agent_name = agent_name
        self._mod = importlib.import_module(f"prompts.{agent_name}_prompts")

    # ── Prompt retrieval ──────────────────────────────────────────────────────

    def system(self, variant: str = "", **kwargs: Any) -> str:
        """
        Return the system prompt, optionally selecting an alternate variant.

        variant=""        → uses SYSTEM
        variant="retry"   → uses SYSTEM_RETRY (falls back to SYSTEM if absent)

        Any kwargs are substituted into the template via str.format().
        """
        attr = f"SYSTEM_{variant.upper()}" if variant else "SYSTEM"
        tmpl: str = getattr(self._mod, attr, self._mod.SYSTEM)
        return tmpl.format(**kwargs) if kwargs else tmpl

    def user(self, **kwargs: Any) -> str:
        """Return the formatted user message."""
        return self._mod.USER_TEMPLATE.format(**kwargs)

    # ── LLM invocation ────────────────────────────────────────────────────────

    def invoke(
        self,
        system_variant: str = "",
        system_kwargs: Optional[Dict[str, Any]] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **user_kwargs: Any,
    ) -> str:
        """Call the LLM and return the raw text response.
        Automatically passes agent_name so call_llm records metrics.
        """
        system_prompt = self.system(system_variant, **(system_kwargs or {}))
        user_msg = self.user(**user_kwargs)
        return call_llm(
            system_prompt=system_prompt,
            user_message=user_msg,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name=self._agent_name,   # ← metrics hook
        )

    def invoke_and_parse(
        self,
        system_variant: str = "",
        system_kwargs: Optional[Dict[str, Any]] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **user_kwargs: Any,
    ) -> Union[Dict, List]:
        """Call the LLM and return the parsed JSON object / array."""
        raw = self.invoke(
            system_variant=system_variant,
            system_kwargs=system_kwargs,
            temperature=temperature,
            max_tokens=max_tokens,
            **user_kwargs,
        )
        return parse_json_from_llm(raw)
