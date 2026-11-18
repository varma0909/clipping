from typing import Any


def split_candidates(
    words: list[dict[str, Any]], min_len: int, max_len: int, max_candidates: int = 80
) -> list[dict[str, Any]]:
    if not words:
        return []
    sentences: list[dict[str, Any]] = []
    sentence_words: list[dict[str, Any]] = []
    for word in words:
        sentence_words.append(word)
        if word["text"].endswith((".", "!", "?", "。", "！", "？")):
            sentences.append(
                {
                    "start": float(sentence_words[0]["start"]),
                    "end": float(sentence_words[-1]["end"]),
                    "words": sentence_words,
                }
            )
            sentence_words = []
    if sentence_words:
        sentences.append(
            {"start": float(sentence_words[0]["start"]), "end": float(sentence_words[-1]["end"]), "words": sentence_words}
        )

    candidates: list[dict[str, Any]] = []
    for first in range(len(sentences)):
        selected: list[dict[str, Any]] = []
        for sentence in sentences[first:]:
            selected.append(sentence)
            start = selected[0]["start"]
            end = selected[-1]["end"]
            duration = end - start
            if duration > max_len:
                break
            if duration >= min_len:
                candidate_words = [word for item in selected for word in item["words"]]
                candidates.append(
                    {
                        "start": start,
                        "end": end,
                        "duration": duration,
                        "text": " ".join(word["text"] for word in candidate_words),
                        "words": candidate_words,
                    }
                )
                break
    if len(candidates) > max_candidates:
        stride = len(candidates) / max_candidates
        candidates = [candidates[int(index * stride)] for index in range(max_candidates)]
    return candidates
