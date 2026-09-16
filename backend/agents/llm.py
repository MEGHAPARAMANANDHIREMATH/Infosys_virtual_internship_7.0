import json
import logging
import re

from django.conf import settings

from agents.exceptions import LLMError

logger = logging.getLogger("agents")

SYSTEM_RULES = """You are a project document analyst.
Extract information ONLY from the provided document text.
Never invent names, dates, owners, tasks, or facts.
If a field is not present, use exactly "Not specified".
Evidence must be a short verbatim quote or close paraphrase of a sentence that appears in the document.
Return valid JSON only.
"""


def llm_enabled() -> bool:
    provider = (getattr(settings, "LLM_PROVIDER", "auto") or "auto").lower()
    if provider in {"grounded", "none", "off"}:
        return False
    if provider == "openai":
        return bool(settings.OPENAI_API_KEY)
    return bool(settings.OPENAI_API_KEY)


def complete_json(user_prompt: str) -> dict | None:
    if not llm_enabled():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        model = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o-mini")
        logger.info("Calling OpenAI chat model=%s", model)
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_RULES},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return _parse_json(content)
    except Exception as exc:
        logger.exception("OpenAI analysis failed: %s", exc)
        raise LLMError("AI analysis is temporarily unavailable. Please try again.") from exc


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            raise LLMError("AI analysis returned invalid JSON.")
        return json.loads(match.group(0))
