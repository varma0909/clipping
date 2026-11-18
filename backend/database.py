import sqlite3
from typing import Any
from backend.config import get_settings


def connect() -> sqlite3.Connection:
    db_path = get_settings().storage_path / "clipforge.db"
    connection = sqlite3.connect(db_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def initialize() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, url TEXT NOT NULL, status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, step TEXT NOT NULL DEFAULT '',
                error TEXT, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clips (
                id TEXT PRIMARY KEY, job_id TEXT NOT NULL, title TEXT NOT NULL,
                start REAL NOT NULL, end REAL NOT NULL, score REAL NOT NULL,
                grade TEXT NOT NULL, breakdown TEXT NOT NULL, reason TEXT NOT NULL,
                hashtags TEXT NOT NULL, video_path TEXT NOT NULL, srt_path TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            """
        )


def create_job(job_id: str, url: str, created_at: float) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO jobs(id,url,status,progress,step,created_at) VALUES(?,?,'queued',0,'Queued',?)",
            (job_id, url, created_at),
        )


def fail_interrupted_jobs() -> int:
    with connect() as db:
        cursor = db.execute(
            """UPDATE jobs SET status='failed', step='Failed',
               error='The backend restarted before this job finished. Start a new job; any completed clips are still available.'
               WHERE status IN ('queued', 'processing')"""
        )
        return cursor.rowcount


def update_job(job_id: str, **fields: Any) -> None:
    allowed = {"status", "progress", "step", "error"}
    values = {key: value for key, value in fields.items() if key in allowed}
    if not values:
        return
    assignments = ", ".join(f"{key}=?" for key in values)
    with connect() as db:
        db.execute(f"UPDATE jobs SET {assignments} WHERE id=?", (*values.values(), job_id))


def get_job(job_id: str) -> sqlite3.Row | None:
    with connect() as db:
        return db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def add_clip(clip: dict[str, Any]) -> None:
    with connect() as db:
        db.execute(
            """INSERT INTO clips(id,job_id,title,start,end,score,grade,breakdown,reason,
               hashtags,video_path,srt_path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                clip["id"], clip["job_id"], clip["title"], clip["start"], clip["end"],
                clip["score"], clip["grade"], clip["breakdown"], clip["reason"],
                clip["hashtags"], clip["video_path"], clip["srt_path"],
            ),
        )


def list_clips(job_id: str) -> list[sqlite3.Row]:
    with connect() as db:
        return db.execute(
            "SELECT * FROM clips WHERE job_id=? ORDER BY score DESC", (job_id,)
        ).fetchall()


def get_clip(clip_id: str) -> sqlite3.Row | None:
    with connect() as db:
        return db.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()


def remove_expired(before: float) -> list[str]:
    with connect() as db:
        rows = db.execute("SELECT id FROM jobs WHERE created_at < ?", (before,)).fetchall()
        job_ids = [str(row["id"]) for row in rows]
        if job_ids:
            placeholders = ",".join("?" for _ in job_ids)
            db.execute(f"DELETE FROM clips WHERE job_id IN ({placeholders})", job_ids)
            db.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", job_ids)
        return job_ids
