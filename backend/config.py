# config.py — Configuration for Alfa Hawk
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# --- Groq AI Configuration (Primary) ---
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_VISION_MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct'
GROQ_TEXT_MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# --- AWS Configuration ---
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME', '')

# --- Application Settings ---
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB
SESSION_TTL_SECONDS = 30 * 60  # 30 minutes auto-cleanup

# --- Supported File Types ---
SUPPORTED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/tiff'}
SUPPORTED_VIDEO_TYPES = {'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska'}
SUPPORTED_AUDIO_TYPES = {'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/ogg', 'audio/flac', 'audio/mp4'}

ALL_SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_VIDEO_TYPES | SUPPORTED_AUDIO_TYPES

# --- Frame Extraction Settings ---
MAX_FRAMES_PER_VIDEO = 50  # Maximum key frames to extract
FRAME_INTERVAL_SECONDS = 1  # Extract a frame every N seconds
FRAME_MAX_DIMENSION = 1280  # Resize frames to fit within this dimension
