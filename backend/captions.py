from pathlib import Path
from typing import Any

STYLE = {
    "bold": {"font": "Arial", "size": 72, "outline": 5, "color": "&H00FFFFFF"},
    "classic": {"font": "Arial", "size": 62, "outline": 3, "color": "&H00FFFFFF"},
    "minimal": {"font": "Arial", "size": 54, "outline": 2, "color": "&H00FFFFFF"},
}


def _timestamp(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _ass_timestamp(seconds: float) -> str:
    total = max(0, round(seconds * 100))
    hours, remainder = divmod(total, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"


def _groups(words: list[dict[str, Any]], max_words: int = 4) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for word in words:
        current.append(word)
        if len(current) >= max_words or word["text"].endswith((".", "!", "?", ",", ";", ":")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def write_captions(
    words: list[dict[str, Any]], clip_start: float, clip_end: float, folder: Path, style_name: str
) -> tuple[Path, Path]:
    selected = [
        {"text": word["text"], "start": max(0.0, float(word["start"]) - clip_start),
         "end": min(clip_end - clip_start, float(word["end"]) - clip_start)}
        for word in words if float(word["end"]) > clip_start and float(word["start"]) < clip_end
    ]
    selected = [word for word in selected if word["end"] > word["start"] and word["text"]]
    groups = _groups(selected)
    srt_lines: list[str] = []
    ass_lines: list[str] = []
    style = STYLE.get(style_name, STYLE["bold"])
    ass_header = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{style['font']},{style['size']},{style['color']},&H0000FFFF,&H00000000,"
        "&H80000000,-1,0,0,0,100,100,0,0,1," + str(style["outline"]) + ",1,2,80,80,600,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for index, group in enumerate(groups, start=1):
        start, end = group[0]["start"], group[-1]["end"]
        srt_lines.extend([str(index), f"{_timestamp(start)} --> {_timestamp(end)}",
                          " ".join(word["text"] for word in group), ""])
        karaoke = []
        for word in group:
            duration = max(1, round((word["end"] - word["start"]) * 100))
            karaoke.append(f"{{\\kf{duration}}}{word['text']}")
        ass_lines.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},Default,,0,0,0,,"
            + " ".join(karaoke)
        )
    srt_path, ass_path = folder / "captions.srt", folder / "captions.ass"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    ass_path.write_text("\n".join(ass_header + ass_lines), encoding="utf-8-sig")
    return srt_path, ass_path
