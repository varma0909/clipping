import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)
_models: dict[str, WhisperModel] = {}


def extract_audio(video_path: Path, wav_path: Path) -> None:
    command = [
        "ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1",
        "-ar", "16000", "-c:a", "pcm_s16le", str(wav_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg was not found. Install FFmpeg and add it to PATH.") from exc
    except subprocess.CalledProcessError as exc:
        logger.error("FFmpeg audio extraction failed: %s", exc.stderr[-1000:])
        raise RuntimeError("Could not extract audio from the downloaded video.") from exc


def transcribe_audio(wav_path: Path, model_size: str, language: str | None = None) -> dict[str, Any]:
    try:
        if model_size not in _models:
            _models[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
        model = _models[model_size]
        segments, info = model.transcribe(
            str(wav_path), word_timestamps=True, language=language or None, vad_filter=True
        )
        words: list[dict[str, Any]] = []
        text_segments: list[dict[str, Any]] = []
        for segment in segments:
            segment_words = []
            for word in segment.words or []:
                item = {"start": float(word.start), "end": float(word.end), "text": word.word.strip()}
                words.append(item)
                segment_words.append(item)
            text_segments.append(
                {"start": float(segment.start), "end": float(segment.end), "text": segment.text.strip(), "words": segment_words}
            )
        transcript = {"language": info.language, "duration": info.duration, "segments": text_segments, "words": words}
        (wav_path.parent / "transcript.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return transcript
    except RuntimeError:
        raise
    except Exception as exc:
        logger.exception("Transcription failed")
        raise RuntimeError("Transcription failed. Check model availability and available memory.") from exc
