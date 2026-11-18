from backend.captions import write_captions


def test_caption_exports_include_clip_relative_word_timing(tmp_path) -> None:
    words = [
        {"text": "Here", "start": 10.0, "end": 10.3},
        {"text": "is", "start": 10.3, "end": 10.5},
        {"text": "your", "start": 10.5, "end": 10.8},
        {"text": "moment!", "start": 10.8, "end": 11.2},
    ]
    srt, ass = write_captions(words, 10.0, 12.0, tmp_path, "bold")
    srt_text = srt.read_text(encoding="utf-8")
    ass_text = ass.read_text(encoding="utf-8-sig")
    assert "00:00:00,000 --> 00:00:01,200" in srt_text
    assert "Here is your moment!" in srt_text
    assert "{\\kf30}Here" in ass_text
    assert "PlayResX: 1080" in ass_text
