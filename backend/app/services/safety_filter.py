"""Safety Filter — psychological safety check for generated story content.

Primary: IBM watsonx.ai (Granite) if configured.
Fallback: Primary LLM via OpenAI-compatible API.
Last resort: keyword-based heuristics.
"""
import json
from app.utils.logger import get_logger

log = get_logger(__name__)

SAFETY_PROMPT = """You are a psychological safety evaluator for a therapeutic story generation system.
Analyze the following story content and evaluate it on these dimensions.

Output ONLY a JSON object:
{
  "safety_score": <float 0.0-1.0, 1.0 = completely safe>,
  "therapeutic_score": <float 0.0-1.0, 1.0 = high therapeutic value>,
  "emotional_tone": "<e.g. hopeful / melancholic / tense / healing>",
  "flags": ["<any concerning elements, empty list if none>"],
  "recommendations": "<suggestions for improvement, empty string if none>",
  "approved": <true if safety_score >= 0.5>
}

Evaluation criteria:
- safety_score: penalize graphic self-harm instructions, glorification of abuse, retraumatizing content
- therapeutic_score: reward emotional growth, empathic portrayal of struggle, moments of insight or hope
- Never penalize stories for depicting difficult emotions — only penalize genuinely harmful instructional content"""

SAFETY_PROMPT_WATSONX = (
    "<|system|>\n" + SAFETY_PROMPT + "\n<|user|>\nStory content:\n\n{content}\n<|assistant|>\n"
)

DANGER_KEYWORDS = [
    "how to kill", "self-harm instructions", "suicide method",
    "detailed violence instructions", "abuse tutorial",
]


def check_safety(content: str) -> dict:
    """Check story content for psychological safety.

    Tries watsonx.ai first, falls back to primary LLM, then keyword heuristics.
    """
    log.info("Running safety filter on content (%d chars)", len(content))
    excerpt = content[:3000]

    # ── Try watsonx.ai ──
    result = _try_watsonx(excerpt)
    if result:
        return result

    # ── Fallback: primary LLM ──
    result = _try_primary_llm(excerpt)
    if result:
        return result

    # ── Last resort: keyword heuristics ──
    return _keyword_check(content)


def _try_watsonx(content: str) -> dict | None:
    try:
        from app.utils.watsonx_client import generate
        prompt = SAFETY_PROMPT_WATSONX.format(content=content)
        response = generate(prompt, max_tokens=512, temperature=0.1)
        if not response:
            return None
        return _parse_safety_json(response)
    except Exception as e:
        log.debug("watsonx.ai unavailable: %s", e)
        return None


def _try_primary_llm(content: str) -> dict | None:
    try:
        from app.utils.llm_client import chat_json
        response = chat_json(
            messages=[
                {"role": "system", "content": SAFETY_PROMPT},
                {"role": "user", "content": f"Story content:\n\n{content}"},
            ],
            temperature=0.1,
            max_tokens=512,
        )
        return _parse_safety_json(response)
    except Exception as e:
        log.warning("Primary LLM safety check failed: %s", e)
        return None


def _parse_safety_json(response: str) -> dict | None:
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(response[start:end])
        else:
            result = json.loads(response)

        result.setdefault("safety_score", 0.85)
        result.setdefault("therapeutic_score", 0.75)
        result.setdefault("emotional_tone", "neutral")
        result.setdefault("flags", [])
        result.setdefault("recommendations", "")
        result.setdefault("approved", result["safety_score"] >= 0.5)

        log.info(
            "Safety check: score=%.2f, therapeutic=%.2f, approved=%s",
            result["safety_score"],
            result["therapeutic_score"],
            result["approved"],
        )
        return result
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        log.warning("Failed to parse safety response: %s", e)
        return None


def _keyword_check(content: str) -> dict:
    """Basic keyword-based safety check as last resort."""
    flags = [kw for kw in DANGER_KEYWORDS if kw in content]
    safety_score = 0.3 if flags else 0.9
    log.info("Keyword safety check: score=%.1f, flags=%s", safety_score, flags)
    return {
        "safety_score": safety_score,
        "therapeutic_score": 0.7,
        "emotional_tone": "unknown",
        "flags": flags,
        "recommendations": "Content reviewed via keyword filter (AI safety check unavailable)." if flags else "",
        "approved": len(flags) == 0,
    }
