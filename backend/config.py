# config.py -- Configuration for Alfa Hawk
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(ROOT_DIR, '.env'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

PORT = int(os.getenv('PORT', '5000'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
ENABLE_DEBUG_ROUTES = os.getenv('ENABLE_DEBUG_ROUTES', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
MAX_UPLOAD_SIZE_BYTES = int(os.getenv('MAX_UPLOAD_SIZE', str(50 * 1024 * 1024)))
MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', '60'))
GLOBAL_DAILY_LIMIT = int(os.getenv('GLOBAL_DAILY_LIMIT', '200'))
RATE_LIMIT_COOLDOWN = int(os.getenv('RATE_LIMIT_COOLDOWN', os.getenv('REQUEST_COOLDOWN_SECONDS', '30')))
CLIENT_HOURLY_LIMIT = int(os.getenv('CLIENT_HOURLY_LIMIT', '1'))
CLIENT_DAILY_LIMIT = int(os.getenv('CLIENT_DAILY_LIMIT', '3'))
IP_HOURLY_LIMIT = int(os.getenv('IP_HOURLY_LIMIT', '3'))
IP_DAILY_LIMIT = int(os.getenv('IP_DAILY_LIMIT', '12'))
MAX_CONCURRENCY_PER_CLIENT = int(os.getenv('MAX_CONCURRENCY_PER_CLIENT', '1'))
MAX_CONCURRENCY_PER_IP = int(os.getenv('MAX_CONCURRENCY_PER_IP', '3'))

MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_BYTES
SESSION_TTL_SECONDS = 30 * 60

SUPPORTED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/tiff'}
SUPPORTED_VIDEO_TYPES = {'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska'}
ALL_SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_VIDEO_TYPES

MAX_FRAMES_PER_VIDEO = 50
FRAME_INTERVAL_SECONDS = 1
FRAME_MAX_DIMENSION = 1280
