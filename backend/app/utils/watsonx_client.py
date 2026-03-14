"""IBM watsonx.ai client for safety filtering and sentiment analysis."""
from app.config import Config
from app.utils.logger import get_logger

log = get_logger(__name__)

_wx_model = None


def _get_model():
    """Lazily initialize watsonx.ai model."""
    global _wx_model
    if _wx_model is not None:
        return _wx_model

    if not Config.WATSONX_API_KEY or not Config.WATSONX_PROJECT_ID:
        log.warning("watsonx.ai credentials not configured")
        return None

    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai import Credentials

    credentials = Credentials(
        url=Config.WATSONX_URL,
        api_key=Config.WATSONX_API_KEY,
    )

    _wx_model = ModelInference(
        model_id="ibm/granite-3-8b-instruct",
        credentials=credentials,
        project_id=Config.WATSONX_PROJECT_ID,
        params={
            "max_new_tokens": 1024,
            "temperature": 0.3,
        },
    )
    log.info("watsonx.ai model initialized: ibm/granite-3-8b-instruct")
    return _wx_model


def generate(prompt: str, *, max_tokens: int = 1024, temperature: float = 0.3) -> str:
    """Generate text using watsonx.ai."""
    model = _get_model()
    if model is None:
        log.warning("watsonx.ai not available, returning empty response")
        return ""

    log.debug("watsonx.ai call: prompt=%d chars", len(prompt))
    response = model.generate_text(
        prompt=prompt,
        params={
            "max_new_tokens": max_tokens,
            "temperature": temperature,
        },
    )
    log.debug("watsonx.ai response: %d chars", len(response) if response else 0)
    return response or ""
