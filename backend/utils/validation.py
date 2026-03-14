import os
import tempfile

import cv2


def validate_media_safety(file_bytes, filename, platform_limits):
    """Validate file extension, size, and basic video safety constraints."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in platform_limits['allowed_extensions']:
        return False, f"Unsupported file extension: {ext}"

    if len(file_bytes) > platform_limits['max_file_size']:
        max_mb = platform_limits['max_file_size'] // (1024 * 1024)
        return False, f"File exceeds maximum size of {max_mb}MB."

    if ext in {'.mp4', '.mov', '.avi'}:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f'upload{ext}')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(file_bytes)

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                return False, "Failed to decode video file. Malformed or unsupported codec."

            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            min_width, min_height = platform_limits['min_resolution']
            if width < min_width or height < min_height:
                return False, (
                    f"Video resolution too low ({int(width)}x{int(height)}). "
                    f"Min {min_width}x{min_height} required."
                )

            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if fps > 0:
                duration = frames / fps
                if duration > platform_limits['max_video_duration']:
                    return False, (
                        f"Video duration ({int(duration)}s) exceeds "
                        f"{platform_limits['max_video_duration']}s limit."
                    )
                if frames < 5:
                    return False, f"Video contains too few frames ({int(frames)})."
            cap.release()

    if ext == '.wav':
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f'upload{ext}')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(file_bytes)

            cap = cv2.VideoCapture(tmp_path)
            if cap.isOpened():
                return False, "Uploaded WAV file appears to be malformed media."
            cap.release()

    return True, None
