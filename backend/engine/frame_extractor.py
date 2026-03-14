# utils/frame_extractor.py -- OpenCV-based video frame extraction (in-memory)
import io
import os
import base64
import tempfile
import logging
import uuid
from PIL import Image

logger = logging.getLogger(__name__)


def extract_key_frames(video_bytes, max_frames=20, interval_seconds=2, max_dimension=1280, original_filename=None):
    """
    Extract key frames from video bytes at regular intervals.
    Returns: dict of {frame_id: {image_bytes, base64, timestamp, frame_number}}
    Everything stays in memory.
    """
    frames = {}

    try:
        import cv2
        import numpy as np

        ext = '.mp4'
        if original_filename:
            _, file_ext = os.path.splitext(original_filename)
            if file_ext:
                ext = file_ext.lower()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f'video{ext}')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(video_bytes)
                tmp.flush()

            file_size = os.path.getsize(tmp_path)
            logger.info("Temp video written: %s (%s bytes, ext=%s)", tmp_path, file_size, ext)

            cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                logger.warning("FFMPEG backend failed, trying MSMF backend...")
                cap = cv2.VideoCapture(tmp_path, cv2.CAP_MSMF)

            if not cap.isOpened():
                logger.warning("MSMF backend failed, trying default backend...")
                cap = cv2.VideoCapture(tmp_path)

            if not cap.isOpened():
                logger.error("Could not open video file with any backend: %s (size=%s, ext=%s)", tmp_path, file_size, ext)
                return frames

            logger.info("Video opened successfully -- backend=%s", cap.getBackendName())

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            frame_interval = int(fps * interval_seconds)
            if frame_interval < 1:
                frame_interval = 1

            frame_indices = list(range(0, total_frames, frame_interval))
            if len(frame_indices) > max_frames:
                step = len(frame_indices) / max_frames
                frame_indices = [frame_indices[int(i * step)] for i in range(max_frames)]

            if 0 not in frame_indices:
                frame_indices.insert(0, 0)
            last_frame = max(0, total_frames - 1)
            if last_frame not in frame_indices:
                frame_indices.append(last_frame)

            for idx in sorted(set(frame_indices)):
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                height, width = frame.shape[:2]
                if max(height, width) > max_dimension:
                    ratio = max_dimension / max(height, width)
                    frame = cv2.resize(frame, (int(width * ratio), int(height * ratio)))

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                buf = io.BytesIO()
                pil_img.save(buf, format='JPEG', quality=85)
                img_bytes = buf.getvalue()

                timestamp = round(idx / fps, 2) if fps > 0 else 0
                frame_id = str(uuid.uuid4())[:8]

                frames[frame_id] = {
                    'image_bytes': img_bytes,
                    'base64': base64.b64encode(img_bytes).decode('utf-8'),
                    'timestamp': timestamp,
                    'timestamp_formatted': _format_timestamp(timestamp),
                    'frame_number': idx,
                    'description': f'Frame at {_format_timestamp(timestamp)}',
                }

            cap.release()
            logger.info("Extracted %s key frames from video (%.1fs)", len(frames), duration)

    except ImportError:
        logger.error("OpenCV not installed -- cannot extract frames")
    except Exception as exc:
        logger.error("Frame extraction failed: %s", exc)

    return frames


def extract_scene_change_frames(video_bytes, threshold=30.0, max_frames=10, max_dimension=1280, original_filename=None):
    """
    Extract frames where significant scene changes occur.
    Uses frame differencing to detect scene transitions.
    """
    frames = {}

    try:
        import cv2
        import numpy as np

        ext = '.mp4'
        if original_filename:
            _, file_ext = os.path.splitext(original_filename)
            if file_ext:
                ext = file_ext.lower()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f'video{ext}')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(video_bytes)
                tmp.flush()

            cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                cap = cv2.VideoCapture(tmp_path, cv2.CAP_MSMF)

            if not cap.isOpened():
                cap = cv2.VideoCapture(tmp_path)

            if not cap.isOpened():
                return frames

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            prev_frame_gray = None
            frame_idx = 0
            scene_changes = []

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if prev_frame_gray is not None:
                    diff = cv2.absdiff(prev_frame_gray, gray)
                    mean_diff = diff.mean()

                    if mean_diff > threshold:
                        scene_changes.append((frame_idx, mean_diff, frame))

                prev_frame_gray = gray
                frame_idx += 1

            cap.release()

            scene_changes.sort(key=lambda item: item[1], reverse=True)
            selected = scene_changes[:max_frames]
            selected.sort(key=lambda item: item[0])

            for idx, intensity, frame in selected:
                height, width = frame.shape[:2]
                if max(height, width) > max_dimension:
                    ratio = max_dimension / max(height, width)
                    frame = cv2.resize(frame, (int(width * ratio), int(height * ratio)))

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                buf = io.BytesIO()
                pil_img.save(buf, format='JPEG', quality=85)
                img_bytes = buf.getvalue()

                timestamp = round(idx / fps, 2)
                frame_id = str(uuid.uuid4())[:8]

                frames[frame_id] = {
                    'image_bytes': img_bytes,
                    'base64': base64.b64encode(img_bytes).decode('utf-8'),
                    'timestamp': timestamp,
                    'timestamp_formatted': _format_timestamp(timestamp),
                    'frame_number': idx,
                    'scene_change_intensity': round(intensity, 2),
                    'description': f'Scene change at {_format_timestamp(timestamp)} (intensity: {intensity:.1f})',
                }

            logger.info("Detected %s scene changes in video", len(frames))

    except ImportError:
        logger.error("OpenCV not installed -- cannot detect scene changes")
    except Exception as exc:
        logger.error("Scene change detection failed: %s", exc)

    return frames


def image_to_frame_entry(image_bytes, filename="evidence_image"):
    """Convert a single image to a frame entry (for uniform processing)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=90)
        jpg_bytes = buf.getvalue()

        frame_id = str(uuid.uuid4())[:8]
        return {
            frame_id: {
                'image_bytes': jpg_bytes,
                'base64': base64.b64encode(jpg_bytes).decode('utf-8'),
                'timestamp': 0,
                'timestamp_formatted': '00:00:00',
                'frame_number': 0,
                'description': f'Evidence image: {filename}',
            }
        }
    except Exception as exc:
        logger.error("Image to frame conversion failed: %s", exc)
        return {}


def _format_timestamp(seconds):
    """Format seconds as HH:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
