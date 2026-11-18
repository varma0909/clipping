import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def render_clip(
    source_path: Path, cropped_path: Path, ass_path: Path, output_path: Path, start: float, end: float
) -> None:
    subtitle_path = ass_path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
    filter_arg = f"subtitles='{subtitle_path}'"
    command = [
        "ffmpeg", "-y", "-ss", str(start), "-i", str(source_path),
        "-i", str(cropped_path), "-t", str(end - start),
        "-filter_complex", f"[1:v]{filter_arg}[v]",
        "-map", "[v]", "-map", "0:a:0?", "-c:v", "libx264", "-crf", "20",
        "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(output_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=max(180, (end - start) * 5))
        if result.returncode:
            logger.error("FFmpeg render failed: %s", result.stderr[-2000:])
            if "libx264" in result.stderr or "Unknown encoder" in result.stderr:
                raise RuntimeError("FFmpeg must be installed with libx264 support.")
            raise RuntimeError("FFmpeg failed while rendering the captioned clip.")
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg was not found. Install FFmpeg and add it to PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Rendering timed out. Try fewer or shorter clips.") from exc
