from backend.segmenter import split_candidates


def _words(text: str, duration: float = 4) -> list[dict]:
    tokens = text.split()
    step = duration / len(tokens)
    return [
        {"text": token, "start": index * step, "end": (index + 1) * step}
        for index, token in enumerate(tokens)
    ]


def test_candidate_starts_and_ends_on_sentence_boundaries() -> None:
    words = _words("This is sentence one. This is sentence two. This is sentence three.", duration=30)
    candidates = split_candidates(words, min_len=12, max_len=20)
    assert candidates
    assert candidates[0]["text"].endswith(".")
    assert candidates[0]["duration"] >= 12


def test_candidate_windows_do_not_exceed_maximum() -> None:
    words = _words("One sentence. Two sentence. Three sentence. Four sentence.", duration=5)
    candidates = split_candidates(words, min_len=4, max_len=6)
    assert all(4 <= item["duration"] <= 6 for item in candidates)


def test_empty_transcript_has_no_candidates() -> None:
    assert split_candidates([], min_len=20, max_len=60) == []
