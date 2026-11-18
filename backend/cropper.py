import logging
from pathlib import Path
from collections import deque
from typing import Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920


def _make_detector() -> Any | None:
    try:
        import mediapipe as mp
        return mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
    except (ImportError, AttributeError, RuntimeError) as exc:
        logger.warning("MediaPipe face detection unavailable; using blurred background layout: %s", exc)
        return None


def _fit_blurred(frame: np.ndarray) -> np.ndarray:
    background_scale = max(OUTPUT_WIDTH / frame.shape[1], OUTPUT_HEIGHT / frame.shape[0])
    background_width = max(OUTPUT_WIDTH, int(frame.shape[1] * background_scale))
    background_height = max(OUTPUT_HEIGHT, int(frame.shape[0] * background_scale))
    background = cv2.resize(frame, (background_width, background_height), interpolation=cv2.INTER_AREA)
    background_x = (background_width - OUTPUT_WIDTH) // 2
    background_y = (background_height - OUTPUT_HEIGHT) // 2
    background = background[background_y:background_y + OUTPUT_HEIGHT, background_x:background_x + OUTPUT_WIDTH]
    background = cv2.GaussianBlur(background, (0, 0), 35)
    scale = min(OUTPUT_WIDTH / frame.shape[1], OUTPUT_HEIGHT / frame.shape[0])
    width, height = max(1, int(frame.shape[1] * scale)), max(1, int(frame.shape[0] * scale))
    foreground = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    x, y = (OUTPUT_WIDTH - width) // 2, (OUTPUT_HEIGHT - height) // 2
    background[y:y + height, x:x + width] = foreground
    return background


def _tracked_crop(frame: np.ndarray, center_x: float) -> np.ndarray:
    height, width = frame.shape[:2]
    crop_width = min(width, int(height * OUTPUT_WIDTH / OUTPUT_HEIGHT))
    left = max(0, min(width - crop_width, int(center_x - crop_width / 2)))
    cropped = frame[:, left:left + crop_width]
    return cv2.resize(cropped, (OUTPUT_WIDTH, OUTPUT_HEIGHT), interpolation=cv2.INTER_AREA)


def create_vertical_video(
    source_path: Path, destination: Path, start: float, end: float
) -> None:
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise RuntimeError("Could not open the downloaded video for vertical cropping.")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    fps = min(max(fps, 1.0), 60.0)
    capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    writer = cv2.VideoWriter(
        str(destination), cv2.VideoWriter_fourcc(*"mp4v"), fps, (OUTPUT_WIDTH, OUTPUT_HEIGHT)
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError("Could not initialize the video encoder for vertical cropping.")
    detector = _make_detector()
    centers: deque[float] = deque(maxlen=7)
    center_x = capture.get(cv2.CAP_PROP_FRAME_WIDTH) / 2
    frame_index = 0
    detected_face = False
    try:
        while capture.get(cv2.CAP_PROP_POS_MSEC) < end * 1000:
            ok, frame = capture.read()
            if not ok:
                break
            if detector is not None and frame_index % max(1, int(fps / 2)) == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = detector.process(rgb)
                if result.detections:
                    width = frame.shape[1]
                    main_face = max(
                        result.detections,
                        key=lambda item: item.location_data.relative_bounding_box.width
                        * item.location_data.relative_bounding_box.height,
                    )
                    box = main_face.location_data.relative_bounding_box
                    centers.append((box.xmin + box.width / 2) * width)
                    center_x = sum(centers) / len(centers)
                    detected_face = True
            output = _tracked_crop(frame, center_x) if detected_face else _fit_blurred(frame)
            writer.write(output)
            frame_index += 1
    finally:
        capture.release()
        writer.release()
        if detector is not None:
            detector.close()
    if frame_index == 0:
        raise RuntimeError("No frames were available in the selected clip.")
