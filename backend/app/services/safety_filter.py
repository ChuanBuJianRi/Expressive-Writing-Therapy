"""Safety Filter — uses IBM watsonx.ai to check content for psychological safety."""
import json
from app.utils.watsonx_client import generate
from app.utils.logger import get_logger

log = get_logger(__name__)

SAFETY_PROMPT_TEMPLATE = """<|system|>
You are a psychological safety evaluator for a therapeutic story generation system.
Analyze the following story content and evaluate it on these dimensions:

1. **Content Safety** (0.0-1.0): Is the content free from harmful triggers?
   - No graphic self-harm instructions
   - No glorification of violence or abuse
   - No content that could retraumatize vulnerable readers

2. **Therapeutic Value** (0.0-1.0): Does the story have therapeutic merit?
   - Characters show emotional growth
   - Struggles are portrayed with empathy
   - There are moments of hope or insight

3. **Emotional Tone**: What is the overall emotional tone?

4. **Recommendations**: Any suggested modifications?

Output ONLY a JSON object:
{{
  "safety_score": <float 0.0-1.0>,
  "therapeutic_score": <float 0.0-1.0>,
  "emotional_tone": "<string>",
  "flags": ["<any concerning elements>"],
  "recommendations": "<suggestions if any>",
  "approved": <true/false>
}}
<|user|>
Story content to evaluate:

{content}
<|assistant|>
"""


def check_safety(content: str) -> dict:
    """Check story content for psychological safety using watsonx.ai (LLM Call #6)."""
    log.info("Running safety filter on content (%d chars)", len(content))

    prompt = SAFETY_PROMPT_TEMPLATE.format(content=content[:3000])
    response = generate(prompt, max_tokens=512, temperature=0.1)

    if not response:
        log.warning("watsonx.ai safety filter unavailable, using fallback")
        return _fallback_safety_check(content)

    try:
        # Try to extract JSON from the response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
        else:
            result = json.loads(response)
    except (json.JSONDecodeError, ValueError):
        log.warning("Failed to parse safety filter response, using fallback")
        return _fallback_safety_check(content)

    # Ensure required fields
    result.setdefault("safety_score", 0.8)
    result.setdefault("therapeutic_score", 0.7)
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


def _fallback_safety_check(content: str) -> dict:
    """Basic keyword-based safety check when watsonx.ai is unavailable."""
    danger_keywords = [
        "自杀方法", "自残方式", "详细描述暴力", "虐待细节",
    ]

    flags = []
    for kw in danger_keywords:
        if kw in content:
            flags.append(kw)

    safety_score = 0.3 if flags else 0.9
    return {
        "safety_score": safety_score,
        "therapeutic_score": 0.7,
        "emotional_tone": "unknown",
        "flags": flags,
        "recommendations": "已使用基础关键词过滤（watsonx.ai不可用）" if flags else "",
        "approved": len(flags) == 0,
    }
