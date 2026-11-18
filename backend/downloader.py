import logging
from pathlib import Path
from urllib.parse import urlparse
import yt_dlp
from yt_dlp.utils import DownloadError

logger = logging.getLogger(__name__)


class VideoDownloadError(RuntimeError):
    pass


def download_video(url: str, destination: Path, max_hours: float) -> tuple[Path, float]:
    host = (urlparse(url).hostname or "").lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}:
        raise VideoDownloadError("Only YouTube video URLs are supported.")
    destination.mkdir(parents=True, exist_ok=True)
    options: dict = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
        "outtmpl": str(destination / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "match_filter": yt_dlp.utils.match_filter_func(f"!is_live & duration <= {int(max_hours * 3600)}"),
    }
    try:
        with yt_dlp.YoutubeDL(options) as client:
            info = client.extract_info(url, download=True)
            duration = float(info.get("duration") or 0)
            if not duration:
                raise VideoDownloadError("Could not determine the video duration.")
            if duration > max_hours * 3600:
                raise VideoDownloadError(f"Video is longer than the {max_hours:g}-hour limit.")
            filepath = Path(client.prepare_filename(info))
            if filepath.suffix.lower() != ".mp4":
                merged_path = filepath.with_suffix(".mp4")
                if merged_path.exists():
                    filepath = merged_path
            if not filepath.exists():
                matches = list(destination.glob("source.*"))
                if not matches:
                    raise VideoDownloadError("YouTube download completed without producing a video file.")
                filepath = matches[0]
            return filepath, duration
    except VideoDownloadError:
        raise
    except DownloadError as exc:
        message = str(exc)
        if "private" in message.lower() or "members-only" in message.lower():
            raise VideoDownloadError("This video is private or members-only and cannot be downloaded.") from exc
        if "age" in message.lower() and "restrict" in message.lower():
            raise VideoDownloadError("This video is age-restricted and cannot be downloaded without access.") from exc
        if "match_filter" in message or "duration" in message.lower():
            raise VideoDownloadError(f"Video exceeds the configured {max_hours:g}-hour limit.") from exc
        logger.exception("YouTube download failed")
        raise VideoDownloadError("Unable to download this video. Check that the link is public and try again.") from exc
