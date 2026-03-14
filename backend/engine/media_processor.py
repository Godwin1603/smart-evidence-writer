# utils/media_processor.py -- In-memory media processing (no disk writes)
import io
import os
import base64
import mimetypes
import logging
import tempfile
from datetime import datetime

from PIL import Image

logger = logging.getLogger(__name__)


def _open_video_capture(path):
    """Try stable OpenCV backends in order to avoid platform-specific decoder issues."""
    try:
        import cv2
    except ImportError:
        return None

    backends = [cv2.CAP_FFMPEG]
    msmf_backend = getattr(cv2, 'CAP_MSMF', None)
    if msmf_backend is not None:
        backends.append(msmf_backend)
    backends.append(None)

    for backend in backends:
        cap = cv2.VideoCapture(path) if backend is None else cv2.VideoCapture(path, backend)
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture()


def get_media_type(filename):
    """Determine media category from filename."""
    mime, _ = mimetypes.guess_type(filename)
    if not mime:
        return 'unknown', mime
    if mime.startswith('image/'):
        return 'image', mime
    if mime.startswith('video/'):
        return 'video', mime
    if mime.startswith('audio/'):
        return 'audio', mime
    return 'unknown', mime


def get_media_metadata(file_bytes, filename):
    """Extract metadata from media file bytes without saving to disk."""
    media_type, mime_type = get_media_type(filename)
    metadata = {
        'filename': filename,
        'media_type': media_type,
        'mime_type': mime_type or 'application/octet-stream',
        'file_size_bytes': len(file_bytes),
        'file_size_mb': round(len(file_bytes) / (1024 * 1024), 2),
        'upload_timestamp': datetime.now().isoformat(),
    }

    if media_type == 'image':
        try:
            img = Image.open(io.BytesIO(file_bytes))
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['image_mode'] = img.mode
            metadata['format'] = img.format
        except Exception as exc:
            logger.warning("Could not read image metadata: %s", exc)
    elif media_type == 'video':
        try:
            metadata.update(_probe_video_metadata(file_bytes))
        except Exception as exc:
            logger.warning("Could not read video metadata: %s", exc)
    elif media_type == 'audio':
        try:
            metadata.update(_probe_audio_metadata(file_bytes, filename))
        except Exception as exc:
            logger.warning("Could not read audio metadata: %s", exc)

    return metadata


def process_image(file_bytes, max_dimension=1280):
    """Resize and prepare image for AI analysis. Returns (processed_bytes, base64_string)."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        processed_bytes = buf.getvalue()
        b64_string = base64.b64encode(processed_bytes).decode('utf-8')
        return processed_bytes, b64_string
    except Exception as exc:
        logger.error("Image processing failed: %s", exc)
        raise


def process_audio(file_bytes, filename):
    """Transcribe audio using SpeechRecognition (in-memory, no disk writes)."""
    transcript = ""
    try:
        import speech_recognition as sr

        ext = os.path.splitext(filename)[1] or '.wav'
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f'audio{ext}')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(file_bytes)

            recognizer = sr.Recognizer()
            if ext.lower() not in ('.wav', '.wave'):
                try:
                    from pydub import AudioSegment

                    audio = AudioSegment.from_file(tmp_path)
                    tmp_path_wav = os.path.join(tmp_dir, 'converted.wav')
                    audio.export(tmp_path_wav, format='wav')
                except Exception as exc:
                    logger.warning("Audio conversion failed: %s", exc)
                    tmp_path_wav = tmp_path
            else:
                tmp_path_wav = tmp_path

            with sr.AudioFile(tmp_path_wav) as source:
                audio_data = recognizer.record(source, duration=300)
                transcript = recognizer.recognize_google(audio_data)

    except ImportError:
        transcript = "[Audio transcription unavailable -- SpeechRecognition not installed]"
    except Exception as exc:
        logger.error("Audio transcription failed: %s", exc)
        transcript = f"[Transcription failed: {str(exc)}]"

    return transcript


def image_bytes_to_base64(image_bytes):
    """Convert raw image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def _probe_video_metadata(file_bytes):
    """Extract basic video metadata by inspecting MP4/MOV headers."""
    meta = {}
    try:
        import cv2

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, 'probe.mp4')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(file_bytes)

            cap = _open_video_capture(tmp_path)
            if cap.isOpened():
                meta['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                meta['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                meta['fps'] = round(cap.get(cv2.CAP_PROP_FPS), 2)
                meta['total_frames'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if meta['fps'] > 0:
                    meta['duration_seconds'] = round(meta['total_frames'] / meta['fps'], 2)
                fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
                if fourcc_int > 0:
                    meta['codec'] = ''.join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
                cap.release()
    except Exception as exc:
        logger.warning("Video metadata extraction failed: %s", exc)

    return meta


def _probe_audio_metadata(file_bytes, filename):
    """Extract basic audio metadata."""
    meta = {}
    try:
        from pydub import AudioSegment

        ext = os.path.splitext(filename)[1].replace('.', '') or 'mp3'
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f'probe.{ext}')
            with open(tmp_path, 'wb') as tmp:
                tmp.write(file_bytes)

            audio = AudioSegment.from_file(tmp_path)
            meta['duration_seconds'] = round(len(audio) / 1000.0, 2)
            meta['channels'] = audio.channels
            meta['sample_rate'] = audio.frame_rate
            meta['sample_width'] = audio.sample_width
    except Exception as exc:
        logger.warning("Audio metadata extraction failed: %s", exc)

    return meta
