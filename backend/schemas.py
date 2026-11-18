from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class JobRequest(BaseModel):
    url: HttpUrl
    num_clips: int = Field(default=8, ge=1, le=20)
    min_len: int = Field(default=20, ge=10, le=180)
    max_len: int = Field(default=60, ge=15, le=300)
    caption_style: str = Field(default="bold", pattern="^(bold|classic|minimal)$")
    language: str | None = Field(default=None, max_length=20)

    @field_validator("url")
    @classmethod
    def youtube_only(cls, value: HttpUrl) -> HttpUrl:
        host = (value.host or "").lower()
        if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}:
            raise ValueError("Enter a valid YouTube video URL.")
        if host.endswith("youtu.be") and not value.path.strip("/"):
            raise ValueError("The YouTube URL must include a video ID.")
        if "youtube.com" in host and value.path != "/watch" and not value.path.startswith(("/shorts/", "/live/", "/embed/")):
            raise ValueError("Enter a valid YouTube video URL.")
        return value

    @model_validator(mode="after")
    def valid_length_range(self) -> "JobRequest":
        if self.max_len <= self.min_len:
            raise ValueError("Maximum clip length must be greater than minimum clip length.")
        return self


class CandidateScore(BaseModel):
    hook_strength: int = Field(ge=0, le=100)
    emotional_impact: int = Field(ge=0, le=100)
    value_or_insight: int = Field(ge=0, le=100)
    standalone_clarity: int = Field(ge=0, le=100)
    pacing_energy: int = Field(ge=0, le=100)
    trend_shareability: int = Field(ge=0, le=100)
    title: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=300)
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    refined_start: float = Field(ge=0)
    refined_end: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered_times(self) -> "CandidateScore":
        if self.refined_end <= self.refined_start:
            raise ValueError("refined_end must be after refined_start")
        return self
