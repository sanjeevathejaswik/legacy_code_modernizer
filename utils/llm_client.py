import json
import re
from typing import Any, Dict, List, Union

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import config


def get_llm(temperature: float = 0.0, max_tokens: int = 4096) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_deployment=config.AZURE_OPENAI_DEPLOYMENT,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    agent_name: str = "",          # optional — enables automatic metrics recording
) -> str:
    llm = get_llm(temperature=temperature, max_tokens=max_tokens)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = llm.invoke(messages)
    content: str = response.content

    # Record LLM call metrics when an agent_name is provided
    if agent_name:
        try:
            from observability.metrics import get_metrics
            get_metrics().record_llm_call(
                agent_name,
                input_chars=len(system_prompt) + len(user_message),
                output_chars=len(content),
            )
        except Exception:
            pass   # metrics must never break the pipeline

    return content


def parse_json_from_llm(content: str) -> Union[Dict, List]:
    # Strip markdown fences (```json ... ``` or ``` ... ```)
    content = re.sub(r"```json\s*", "", content)
    content = re.sub(r"```\s*", "", content)
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Fallback: find the outermost JSON object
    obj_match = re.search(r"\{.*\}", content, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: find the outermost JSON array
    arr_match = re.search(r"\[.*\]", content, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse JSON from LLM response. "
        f"First 500 chars: {content[:500]}"
    )
