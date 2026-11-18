import logging
import json
import re
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend import database
from backend.config import get_settings
from backend.pipeline import run_pipeline
from backend.schemas import JobRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
_cleanup_stop = threading.Event()


def cleanup_expired() -> None:
    cutoff = time.time() - get_settings().retention_hours * 3600
    for job_id in database.remove_expired(cutoff):
        directory = get_settings().storage_path / job_id
        if directory.exists() and directory.is_dir():
            shutil.rmtree(directory)
            logger.info("Removed expired job files for %s", job_id)


def _cleanup_loop() -> None:
    while not _cleanup_stop.wait(3600):
        try:
            cleanup_expired()
        except Exception:
            logger.exception("Scheduled storage cleanup failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    interrupted = database.fail_interrupted_jobs()
    if interrupted:
        logger.warning("Marked %s interrupted jobs as failed after backend restart", interrupted)
    cleanup_expired()
    _cleanup_stop.clear()
    thread = threading.Thread(target=_cleanup_loop, name="clipforge-cleanup", daemon=True)
    thread.start()
    yield
    _cleanup_stop.set()
    thread.join(timeout=2)


app = FastAPI(title="ClipForge API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs", status_code=202)
def create_job(payload: JobRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    database.create_job(job_id, str(payload.url), time.time())
    background_tasks.add_task(run_pipeline, job_id, payload.model_dump(mode="json"))
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = database.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "job_id": job["id"], "status": job["status"], "progress": job["progress"],
        "step": job["step"], "error": job["error"],
    }


def _serialize_clip(clip: sqlite3.Row) -> dict:
    return {
        "id": clip["id"], "title": clip["title"], "start": clip["start"], "end": clip["end"],
        "duration": round(clip["end"] - clip["start"], 1), "score": clip["score"],
        "grade": clip["grade"], "breakdown": json.loads(clip["breakdown"]),
        "reason": clip["reason"], "hashtags": json.loads(clip["hashtags"]),
        "preview_url": f"/api/clips/{clip['id']}/preview",
        "download_url": f"/api/clips/{clip['id']}/download",
        "srt_url": f"/api/clips/{clip['id']}/download/srt",
    }


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._ -]", "", value).strip(" .")
    return safe[:80] or "clip"


@app.get("/api/jobs/{job_id}/clips")
def job_clips(job_id: str) -> list[dict]:
    job = database.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return [_serialize_clip(clip) for clip in database.list_clips(job_id)]


def _file_for_clip(clip_id: str, field: str) -> Path:
    clip = database.get_clip(clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found.")
    path = Path(clip[field])
    if not path.is_file():
        raise HTTPException(status_code=410, detail="This clip has expired and its file was removed.")
    return path


@app.get("/api/clips/{clip_id}/preview")
def clip_preview(clip_id: str) -> FileResponse:
    path = _file_for_clip(clip_id, "video_path")
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/clips/{clip_id}/download")
def download_clip(clip_id: str) -> FileResponse:
    clip = database.get_clip(clip_id)
    path = _file_for_clip(clip_id, "video_path")
    return FileResponse(path, media_type="video/mp4", filename=f"{_safe_filename(clip['title'])}.mp4")


@app.get("/api/clips/{clip_id}/download/srt")
def download_srt(clip_id: str) -> FileResponse:
    path = _file_for_clip(clip_id, "srt_path")
    return FileResponse(path, media_type="application/x-subrip", filename="captions.srt")


@app.get("/api/jobs/{job_id}/download-all")
def download_all(job_id: str) -> FileResponse:
    job = database.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    clips = database.list_clips(job_id)
    if not clips:
        raise HTTPException(status_code=409, detail="No clips are ready to download.")
    archive_path = get_settings().storage_path / job_id / "clips.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, clip in enumerate(clips, start=1):
            video = Path(clip["video_path"])
            subtitle = Path(clip["srt_path"])
            title = _safe_filename(clip["title"])
            if video.is_file():
                archive.write(video, f"{index:02d}-{clip['grade']}-{title}.mp4")
            if subtitle.is_file():
                archive.write(subtitle, f"{index:02d}-{clip['grade']}-{title}.srt")
    return FileResponse(archive_path, media_type="application/zip", filename="clipforge-clips.zip")
