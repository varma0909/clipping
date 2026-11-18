import json
import logging
import re
from typing import Any
import httpx

from backend.config import get_settings
from backend.schemas import CandidateScore

logger = logging.getLogger(__name__)
WEIGHTS = {
    "hook_strength": 0.25,
    "emotional_impact": 0.20,
    "value_or_insight": 0.15,
    "standalone_clarity": 0.15,
    "pacing_energy": 0.15,
    "trend_shareability": 0.10,
}


def score_value(score: CandidateScore) -> float:
    return round(sum(getattr(score, key) * weight for key, weight in WEIGHTS.items()), 1)


def grade_for(score: float) -> str:
    if score >= 85:
        return "S"
    if score >= 70:
        return "A"
    if score >= 55:
        return "B"
    return "C"


def _request_content(candidates: list[dict[str, Any]], language: str | None) -> str:
    records = [
        {"index": i, "start": item["start"], "end": item["end"], "transcript": item["text"]}
        for i, item in enumerate(candidates)
    ]
    return (
        "Rate each video transcript as a standalone short-form clip. Return only a JSON object with a 'scores' "
        "array containing one object per input index, in input order. Each object must contain index, hook_strength, emotional_impact, "
        "value_or_insight, standalone_clarity, pacing_energy, trend_shareability (integer 0-100), title, "
        "reason, hashtags (array of strings), refined_start and refined_end (absolute seconds within that "
        "candidate's start/end). Do not invent claims. Keep title catchy and reason to one sentence. "
        f"Language: {language or 'detect from transcript'}.\nINPUT:\n{json.dumps(records, ensure_ascii=False)}"
    )


def _call_provider(prompt: str) -> str:
    settings = get_settings()
    if settings.llm_provider.lower() == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Add OPENAI_API_KEY to backend/.env or choose a configured LLM provider.")
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.llm_model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "Return strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    elif settings.llm_provider.lower() == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Add ANTHROPIC_API_KEY to backend/.env or choose a configured LLM provider.")
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model if settings.llm_model.startswith("claude-") else "claude-3-5-sonnet-latest",
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=90,
        )
        response.raise_for_status()
        content = response.json()["content"][0]["text"]
    elif settings.llm_provider.lower() == "ollama":
        base_url = settings.ollama_base_url.rstrip("/")
        try:
            response = httpx.post(
                f"{base_url}/api/chat",
                json={
                    "model": settings.llm_model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": "Return strict JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=180,
            )
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Could not connect to Ollama. Start Ollama and make sure it is listening at "
                f"{base_url}."
            ) from exc
        if response.status_code == 404:
            raise RuntimeError(
                f"Ollama model '{settings.llm_model}' is not installed. Run "
                f"`ollama pull {settings.llm_model}` and retry."
            )
        response.raise_for_status()
        content = response.json()["message"]["content"]
    else:
        raise RuntimeError("LLM_PROVIDER must be 'ollama', 'openai', or 'anthropic'.")
    return str(content)


def _decode_scores(response: str, candidates: list[dict[str, Any]]) -> list[CandidateScore]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip(), flags=re.IGNORECASE)
    payload = json.loads(cleaned)
    if isinstance(payload, dict):
        payload = payload.get("scores", payload.get("clips", payload.get("results")))
    if not isinstance(payload, list) or len(payload) != len(candidates):
        raise ValueError("LLM response must contain one score object per candidate.")
    validated: list[CandidateScore] = []
    for raw, candidate in zip(payload, candidates):
        if not isinstance(raw, dict):
            raise ValueError("LLM returned a non-object score.")
        start = float(candidate["start"])
        end = float(candidate["end"])
        raw["refined_start"] = max(start, min(float(raw.get("refined_start", start)), end))
        raw["refined_end"] = max(start, min(float(raw.get("refined_end", end)), end))
        validated.append(CandidateScore.model_validate(raw))
    return validated


def _score_batch(candidates: list[dict[str, Any]], language: str | None) -> list[dict[str, Any]]:
    prompt = _request_content(candidates, language)
    for attempt in range(2):
        try:
            response = _call_provider(prompt)
            scores = _decode_scores(response, candidates)
            return [{**candidate, "evaluation": score, "score": score_value(score), "grade": grade_for(score_value(score))}
                    for candidate, score in zip(candidates, scores)]
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            if attempt == 0:
                logger.warning("Invalid LLM scoring response; retrying once: %s", exc)
                prompt += "\nYour prior response was invalid. Return exactly one valid JSON score object per input."
                continue
            raise RuntimeError("The clip scoring service returned invalid data after one retry.") from exc
        except httpx.HTTPError as exc:
            logger.exception("LLM API request failed")
            raise RuntimeError(f"Could not reach the configured LLM provider: {exc}") from exc
    raise RuntimeError("Could not score this batch of video moments.")


def score_candidates(candidates: list[dict[str, Any]], language: str | None = None) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for offset in range(0, len(candidates), 10):
        scored.extend(_score_batch(candidates[offset:offset + 10], language))
    return scored


def choose_top_clips(
    scored: list[dict[str, Any]], count: int, min_len: int, max_len: int
) -> list[dict[str, Any]]:
    ordered = sorted(scored, key=lambda clip: clip["score"], reverse=True)
    selected: list[dict[str, Any]] = []
    for clip in ordered:
        start, end = clip["evaluation"].refined_start, clip["evaluation"].refined_end
        if not min_len <= end - start <= max_len:
            start, end = clip["start"], clip["end"]
        if any(start < current["evaluation"].refined_end and end > current["evaluation"].refined_start for current in selected):
            continue
        clip["start"], clip["end"] = start, end
        clip["evaluation"].refined_start = start
        clip["evaluation"].refined_end = end
        selected.append(clip)
        if len(selected) == count:
            break
    return selected
