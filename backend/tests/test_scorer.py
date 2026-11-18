import json
from types import SimpleNamespace

import backend.scorer as scorer
from backend.scorer import choose_top_clips, grade_for, score_candidates, score_value
from backend.schemas import CandidateScore


def _score(value: int) -> CandidateScore:
    return CandidateScore(
        hook_strength=value, emotional_impact=value, value_or_insight=value,
        standalone_clarity=value, pacing_energy=value, trend_shareability=value,
        title="A good title", reason="A clear reason.", hashtags=["shorts"],
        refined_start=1, refined_end=10,
    )


def test_weighted_score_and_grade_boundaries() -> None:
    assert score_value(_score(100)) == 100
    assert grade_for(85) == "S"
    assert grade_for(84.9) == "A"
    assert grade_for(70) == "A"
    assert grade_for(55) == "B"
    assert grade_for(54.9) == "C"


def test_refined_times_must_be_ordered() -> None:
    values = _score(80).model_dump()
    values["refined_end"] = values["refined_start"]
    try:
        CandidateScore.model_validate(values)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid refined timestamps should be rejected.")


def test_invalid_llm_json_is_retried_once(monkeypatch) -> None:
    candidate = {"start": 1.0, "end": 40.0, "text": "A complete candidate."}
    calls = iter(["not json", json.dumps({"scores": [{
        **_score(80).model_dump(), "index": 0,
    }]})])
    monkeypatch.setattr("backend.scorer._call_provider", lambda _: next(calls))
    result = score_candidates([candidate])
    assert len(result) == 1
    assert result[0]["grade"] == "A"


def test_top_clip_selection_deduplicates_overlap_and_preserves_length() -> None:
    first_score = _score(95)
    first_score.refined_start, first_score.refined_end = 1, 10
    second_score = _score(90)
    second_score.refined_start, second_score.refined_end = 20, 42
    third_score = _score(80)
    third_score.refined_start, third_score.refined_end = 45, 70
    scored = [
        {"start": 0, "end": 25, "score": 95, "evaluation": first_score},
        {"start": 20, "end": 45, "score": 90, "evaluation": second_score},
        {"start": 50, "end": 75, "score": 80, "evaluation": third_score},
    ]
    selected = choose_top_clips(scored, 2, min_len=20, max_len=30)
    assert len(selected) == 2
    assert selected[0]["end"] - selected[0]["start"] == 25
    assert selected[1]["start"] == 45


def test_ollama_provider_uses_configured_local_model(monkeypatch) -> None:
    settings = SimpleNamespace(
        llm_provider="ollama",
        llm_model="qwen2.5:3b",
        ollama_base_url="http://127.0.0.1:11434/",
    )
    monkeypatch.setattr(scorer, "get_settings", lambda: settings)

    class Response:
        status_code = 200

        @staticmethod
        def raise_for_status() -> None:
            return None

        @staticmethod
        def json() -> dict:
            return {"message": {"content": '{"scores": []}'}}

    def fake_post(url: str, **kwargs):
        assert url == "http://127.0.0.1:11434/api/chat"
        assert kwargs["json"]["model"] == "qwen2.5:3b"
        assert kwargs["json"]["format"] == "json"
        return Response()

    monkeypatch.setattr(scorer.httpx, "post", fake_post)
    assert scorer._call_provider("score this") == '{"scores": []}'
