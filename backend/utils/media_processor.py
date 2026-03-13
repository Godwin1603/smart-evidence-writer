# utils/media_processor.py — In-memory media processing (no disk writes)
import io
import os
import base64
import mimetypes
import logging
import tempfile
import struct
from datetime import datetime
from PIL import Image

logger = logging.getLogger(__name__)


def get_media_type(filename):
    """Determine media category from filename."""
    mime, _ = mimetypes.guess_type(filename)
    if not mime:
        return 'unknown', mime
    if mime.startswith('image/'):
        return 'image', mime
    elif mime.startswith('video/'):
        return 'video', mime
    elif mime.startswith('audio/'):
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
        except Exception as e:
            logger.warning(f"Could not read image metadata: {e}")

    elif media_type == 'video':
        try:
            metadata.update(_probe_video_metadata(file_bytes))
        except Exception as e:
            logger.warning(f"Could not read video metadata: {e}")

    elif media_type == 'audio':
        try:
            metadata.update(_probe_audio_metadata(file_bytes, filename))
        except Exception as e:
            logger.warning(f"Could not read audio metadata: {e}")

    return metadata


def process_image(file_bytes, max_dimension=1280):
    """Resize and prepare image for AI analysis. Returns (processed_bytes, base64_string)."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        # Resize if needed
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Save to in-memory buffer as JPEG
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        processed_bytes = buf.getvalue()
        b64_string = base64.b64encode(processed_bytes).decode('utf-8')
        return processed_bytes, b64_string
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise


def process_audio(file_bytes, filename):
    """Transcribe audio using SpeechRecognition (in-memory, no disk writes)."""
    transcript = ""
    try:
        import speech_recognition as sr

        # Write to a temporary file (SpeechRecognition needs a file path)
        ext = os.path.splitext(filename)[1] or '.wav'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            recognizer = sr.Recognizer()
            # Convert to WAV if needed using pydub
            if ext.lower() not in ('.wav', '.wave'):
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(tmp_path)
                    wav_tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                    audio.export(wav_tmp.name, format='wav')
                    wav_tmp.close()
                    tmp_path_wav = wav_tmp.name
                except Exception as e:
                    logger.warning(f"Audio conversion failed: {e}")
                    tmp_path_wav = tmp_path
            else:
                tmp_path_wav = tmp_path

            with sr.AudioFile(tmp_path_wav) as source:
                audio_data = recognizer.record(source, duration=300)  # max 5 min
                transcript = recognizer.recognize_google(audio_data)
        finally:
            # Clean up temp files
            try:
                os.unlink(tmp_path)
                if 'tmp_path_wav' in locals() and tmp_path_wav != tmp_path:
                    os.unlink(tmp_path_wav)
            except OSError:
                pass

    except ImportError:
        transcript = "[Audio transcription unavailable — SpeechRecognition not installed]"
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        transcript = f"[Transcription failed: {str(e)}]"

    return transcript


def image_bytes_to_base64(image_bytes):
    """Convert raw image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def _probe_video_metadata(file_bytes):
    """Extract basic video metadata by inspecting MP4/MOV headers."""
    meta = {}
    try:
        # Try OpenCV for more detailed metadata
        import cv2
        import numpy as np
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            cap = cv2.VideoCapture(tmp_path)
            if cap.isOpened():
                meta['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                meta['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                meta['fps'] = round(cap.get(cv2.CAP_PROP_FPS), 2)
                meta['total_frames'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if meta['fps'] > 0:
                    meta['duration_seconds'] = round(meta['total_frames'] / meta['fps'], 2)
                cap.release()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Video metadata extraction failed: {e}")

    return meta


def _probe_audio_metadata(file_bytes, filename):
    """Extract basic audio metadata."""
    meta = {}
    try:
        from pydub import AudioSegment
        ext = os.path.splitext(filename)[1].replace('.', '') or 'mp3'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            audio = AudioSegment.from_file(tmp_path)
            meta['duration_seconds'] = round(len(audio) / 1000.0, 2)
            meta['channels'] = audio.channels
            meta['sample_rate'] = audio.frame_rate
            meta['sample_width'] = audio.sample_width
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Audio metadata extraction failed: {e}")

    return meta
