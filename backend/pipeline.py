import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from backend import database
from backend.config import get_settings
from backend.captions import write_captions
from backend.cropper import create_vertical_video
from backend.downloader import download_video, get_video_duration
from backend.renderer import render_clip
from backend.scorer import choose_top_clips, score_candidates
from backend.segmenter import split_candidates
from backend.transcriber import extract_audio, transcribe_audio

logger = logging.getLogger(__name__)


def run_pipeline(job_id: str, request: dict[str, Any]) -> None:
    job_dir = get_settings().storage_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    def progress(step: str, percent: int) -> None:
        database.update_job(job_id, status="processing", step=step, progress=percent)

    try:
        if request.get("source_path"):
            progress("Preparing uploaded video", 5)
            source = Path(request["source_path"])
            duration = get_video_duration(source)
            max_duration = get_settings().max_video_hours * 3600
            if duration > max_duration:
                raise RuntimeError(
                    f"Video is longer than the {get_settings().max_video_hours:g}-hour limit."
                )
        else:
            progress("Downloading", 5)
            source, _ = download_video(request["url"], job_dir, get_settings().max_video_hours)
        audio = job_dir / "audio.wav"
        progress("Transcribing", 22)
        extract_audio(source, audio)
        transcript = transcribe_audio(audio, get_settings().whisper_model, request.get("language"))
        progress("Finding best moments", 42)
        candidates = split_candidates(transcript["words"], request["min_len"], request["max_len"])
        if not candidates:
            raise RuntimeError(
                f"No complete transcript segments between {request['min_len']} and {request['max_len']} seconds were found."
            )
        progress("Grading", 52)
        scored = score_candidates(candidates, transcript.get("language"))
        selected = choose_top_clips(
            scored, request["num_clips"], request["min_len"], request["max_len"]
        )
        if not selected:
            raise RuntimeError("The scoring service did not return any usable clips.")
        total_clips = len(selected)
        progress("Cropping to 9:16", 62)
        for index, clip in enumerate(selected):
            clip_number = index + 1
            progress(
                f"Cropping to 9:16 · clip {clip_number}/{total_clips}",
                62 + int(34 * index / total_clips),
            )
            clip_id = str(uuid.uuid4())
            clip_dir = job_dir / clip_id
            clip_dir.mkdir(parents=True, exist_ok=True)
            crop_path = clip_dir / "vertical-silent.mp4"
            video_path = clip_dir / "clip.mp4"
            words = clip["words"]
            srt_path, ass_path = write_captions(
                words, clip["start"], clip["end"], clip_dir, request["caption_style"]
            )
            create_vertical_video(source, crop_path, clip["start"], clip["end"])
            progress(
                f"Adding captions · clip {clip_number}/{total_clips}",
                62 + int(34 * (index + 0.5) / total_clips),
            )
            render_clip(source, crop_path, ass_path, video_path, clip["start"], clip["end"])
            evaluation = clip["evaluation"]
            breakdown = {
                "hook_strength": evaluation.hook_strength,
                "emotional_impact": evaluation.emotional_impact,
                "value_or_insight": evaluation.value_or_insight,
                "standalone_clarity": evaluation.standalone_clarity,
                "pacing_energy": evaluation.pacing_energy,
                "trend_shareability": evaluation.trend_shareability,
            }
            database.add_clip(
                {
                    "id": clip_id, "job_id": job_id, "title": evaluation.title,
                    "start": clip["start"], "end": clip["end"], "score": clip["score"],
                    "grade": clip["grade"], "breakdown": json.dumps(breakdown),
                    "reason": evaluation.reason, "hashtags": json.dumps(evaluation.hashtags),
                    "video_path": str(video_path), "srt_path": str(srt_path),
                }
            )
            crop_path.unlink(missing_ok=True)
            progress(
                f"Adding captions · clip {clip_number}/{total_clips}",
                62 + int(34 * clip_number / total_clips),
            )
        progress("Done", 100)
        database.update_job(job_id, status="done", step="Done", progress=100)
    except Exception as exc:
        logger.exception("ClipForge job %s failed", job_id)
        database.update_job(job_id, status="failed", step="Failed", error=str(exc))
        try:
            (job_dir / "failure.txt").write_text(str(exc), encoding="utf-8")
        except OSError:
            logger.warning("Could not save error details for job %s", job_id)
