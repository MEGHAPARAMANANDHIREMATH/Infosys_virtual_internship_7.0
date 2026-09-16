class AgentAnalysisError(Exception):
    """User-facing analysis failure (bad input, missing text, invalid agent)."""


class LLMError(Exception):
    """LLM provider failure."""
