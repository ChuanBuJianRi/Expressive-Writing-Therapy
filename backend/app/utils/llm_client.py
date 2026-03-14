"""Unified LLM client using the OpenAI SDK (compatible with any OpenAI-format API)."""
from openai import OpenAI
from app.config import Config
from app.utils.logger import get_logger

log = get_logger(__name__)

_primary_client = None
_boost_client = None


def _get_primary_client() -> OpenAI:
    global _primary_client
    if _primary_client is None:
        _primary_client = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
        )
    return _primary_client


def _get_boost_client() -> OpenAI | None:
    global _boost_client
    if not Config.LLM_BOOST_API_KEY:
        return None
    if _boost_client is None:
        _boost_client = OpenAI(
            api_key=Config.LLM_BOOST_API_KEY,
            base_url=Config.LLM_BOOST_BASE_URL,
        )
    return _boost_client


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.8,
    max_tokens: int = 4096,
    use_boost: bool = False,
    response_format: dict | None = None,
) -> str:
    """Send a chat completion request and return the assistant message content."""
    if use_boost:
        client = _get_boost_client()
        model = model or Config.LLM_BOOST_MODEL_NAME
        if client is None:
            log.warning("Boost LLM not configured, falling back to primary")
            client = _get_primary_client()
            model = model or Config.LLM_MODEL_NAME
    else:
        client = _get_primary_client()
        model = model or Config.LLM_MODEL_NAME

    log.debug("LLM call: model=%s, messages=%d, temp=%.1f", model, len(messages), temperature)

    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    log.debug("LLM response: %d chars", len(content) if content else 0)
    return content or ""


def chat_json(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    use_boost: bool = False,
) -> str:
    """Chat with JSON response format."""
    return chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        use_boost=use_boost,
        response_format={"type": "json_object"},
    )
