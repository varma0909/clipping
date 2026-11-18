import sqlite3
from backend import database


def test_backend_restart_marks_only_queued_and_processing_jobs_failed(monkeypatch) -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """CREATE TABLE jobs(id TEXT, status TEXT, step TEXT, error TEXT);
           INSERT INTO jobs VALUES('queued','queued','Queued',NULL);
           INSERT INTO jobs VALUES('running','processing','Grading',NULL);
           INSERT INTO jobs VALUES('done','done','Done',NULL);"""
    )
    monkeypatch.setattr(database, "connect", lambda: connection)

    assert database.fail_interrupted_jobs() == 2
    states = dict(connection.execute("SELECT id,status FROM jobs"))
    assert states == {"queued": "failed", "running": "failed", "done": "done"}
