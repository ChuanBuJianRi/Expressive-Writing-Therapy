"""Dynamic LLM configuration endpoint."""
from flask import Blueprint, request, jsonify
from app.utils.logger import get_logger

log = get_logger(__name__)
config_bp = Blueprint("config", __name__)

PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-1.5-pro",
    },
}


@config_bp.route("/llm", methods=["POST"])
def set_llm_config():
    """Dynamically reconfigure the primary LLM client.

    Request body:
    {
        "provider": "openai" | "anthropic" | "google",
        "api_key": "sk-...",
        "model": "gpt-4o",
        "base_url": "https://..."   (optional override)
    }
    """
    data = request.get_json() or {}
    provider = data.get("provider", "openai")
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "").strip()
    base_url = data.get("base_url", "").strip()

    if not api_key:
        return jsonify({"error": "api_key is required"}), 400

    provider_cfg = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["openai"])
    resolved_url   = base_url  or provider_cfg["base_url"]
    resolved_model = model     or provider_cfg["default_model"]

    # Re-initialise OpenAI-compatible client
    from openai import OpenAI
    import app.utils.llm_client as lc
    lc._primary_client = OpenAI(api_key=api_key, base_url=resolved_url)

    # Patch Config so every subsequent call picks up the new values
    from app.config import Config
    Config.LLM_API_KEY    = api_key
    Config.LLM_BASE_URL   = resolved_url
    Config.LLM_MODEL_NAME = resolved_model

    log.info("LLM reconfigured: provider=%s model=%s url=%s", provider, resolved_model, resolved_url)

    return jsonify({
        "status": "ok",
        "provider": provider,
        "model": resolved_model,
        "base_url": resolved_url,
    })


@config_bp.route("/llm", methods=["GET"])
def get_llm_config():
    """Return current config (key is masked)."""
    from app.config import Config
    return jsonify({
        "configured": bool(Config.LLM_API_KEY),
        "model":      Config.LLM_MODEL_NAME,
        "base_url":   Config.LLM_BASE_URL,
    })
