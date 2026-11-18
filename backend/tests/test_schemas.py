import pytest
from pydantic import ValidationError

from backend.schemas import JobOptions, JobRequest


def test_job_request_accepts_youtube_and_defaults() -> None:
    request = JobRequest(url="https://youtu.be/abc123")
    assert request.num_clips == 8
    assert request.min_len == 20
    assert request.max_len == 60
    assert request.caption_style == "bold"


@pytest.mark.parametrize(
    "url",
    ["https://example.com/watch?v=abc", "https://youtube.com.evil.example/watch?v=abc"],
)
def test_job_request_rejects_non_youtube_hosts(url: str) -> None:
    with pytest.raises(ValidationError):
        JobRequest(url=url)


def test_job_request_rejects_invalid_clip_range() -> None:
    with pytest.raises(ValidationError):
        JobRequest(url="https://youtu.be/abc123", min_len=60, max_len=60)


def test_job_options_rejects_invalid_clip_range() -> None:
    with pytest.raises(ValidationError):
        JobOptions(min_len=60, max_len=60)
