# utils/frame_extractor.py — OpenCV-based video frame extraction (in-memory)
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

        # Determine file extension from original filename
        ext = '.mp4'
        if original_filename:
            _, file_ext = os.path.splitext(original_filename)
            if file_ext:
                ext = file_ext.lower()

        # Write video to temp file for OpenCV (it needs a file path)
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(tmp_fd, 'wb') as tmp:
                tmp.write(video_bytes)
                tmp.flush()

            file_size = os.path.getsize(tmp_path)
            logger.info(f"Temp video written: {tmp_path} ({file_size} bytes, ext={ext})")

            # Try opening with multiple backends
            cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                logger.warning("FFMPEG backend failed, trying MSMF backend...")
                cap = cv2.VideoCapture(tmp_path, cv2.CAP_MSMF)

            if not cap.isOpened():
                logger.warning("MSMF backend failed, trying default backend...")
                cap = cv2.VideoCapture(tmp_path)

            if not cap.isOpened():
                logger.error(f"Could not open video file with any backend: {tmp_path} (size={file_size}, ext={ext})")
                return frames

            logger.info(f"Video opened successfully — backend={cap.getBackendName()}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # Calculate frame interval
            frame_interval = int(fps * interval_seconds)
            if frame_interval < 1:
                frame_interval = 1

            # Limit total frames extracted
            frame_indices = list(range(0, total_frames, frame_interval))
            if len(frame_indices) > max_frames:
                # Evenly space the frames
                step = len(frame_indices) / max_frames
                frame_indices = [frame_indices[int(i * step)] for i in range(max_frames)]

            # Always include first and last frame
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

                # Resize if needed
                h, w = frame.shape[:2]
                if max(h, w) > max_dimension:
                    ratio = max_dimension / max(h, w)
                    frame = cv2.resize(frame, (int(w * ratio), int(h * ratio)))

                # Convert BGR to RGB and then to JPEG bytes
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
                    'description': f'Frame at {_format_timestamp(timestamp)}'
                }

            cap.release()
            logger.info(f"Extracted {len(frames)} key frames from video ({duration:.1f}s)")

        finally:
            try:
                if tmp_path:
                    os.unlink(tmp_path)
            except OSError:
                pass

    except ImportError:
        logger.error("OpenCV not installed — cannot extract frames")
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")

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

        # Determine file extension from original filename
        ext = '.mp4'
        if original_filename:
            _, file_ext = os.path.splitext(original_filename)
            if file_ext:
                ext = file_ext.lower()

        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(tmp_fd, 'wb') as tmp:
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

            # Take top N scene changes by intensity
            scene_changes.sort(key=lambda x: x[1], reverse=True)
            selected = scene_changes[:max_frames]
            selected.sort(key=lambda x: x[0])  # Sort by time

            for idx, intensity, frame in selected:
                h, w = frame.shape[:2]
                if max(h, w) > max_dimension:
                    ratio = max_dimension / max(h, w)
                    frame = cv2.resize(frame, (int(w * ratio), int(h * ratio)))

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
                    'description': f'Scene change at {_format_timestamp(timestamp)} (intensity: {intensity:.1f})'
                }

            logger.info(f"Detected {len(frames)} scene changes in video")

        finally:
            try:
                if tmp_path:
                    os.unlink(tmp_path)
            except OSError:
                pass

    except ImportError:
        logger.error("OpenCV not installed — cannot detect scene changes")
    except Exception as e:
        logger.error(f"Scene change detection failed: {e}")

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
                'description': f'Evidence image: {filename}'
            }
        }
    except Exception as e:
        logger.error(f"Image conversion failed: {e}")
        return {}


def _format_timestamp(seconds):
    """Format seconds into HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
