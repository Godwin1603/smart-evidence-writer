# app.py — Alfa Hawk: Flask backend with in-memory storage
import os
import sys
import io
import uuid
import time
import hashlib
import logging
import threading
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, Response, abort
from flask_cors import CORS
from dotenv import load_dotenv

# V2.1 Platform Readiness
import threading
from collections import defaultdict
from functools import wraps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(ROOT_DIR, '.env'))
load_dotenv(os.path.join(BASE_DIR, '.env'))


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logging.getLogger('alfa-hawk').warning(
            "Invalid integer for %s=%r. Falling back to %s.",
            name,
            value,
            default,
        )
        return default


def _env_int_with_alias(primary_name, alias_name, default):
    primary_value = os.getenv(primary_name)
    if primary_value is not None:
        return _env_int(primary_name, default)
    return _env_int(alias_name, default)


def _env_csv(name):
    value = os.getenv(name, '')
    return [item.strip() for item in value.split(',') if item.strip()]

# ─────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('alfa-hawk')

# ─────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────
DEFAULT_FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')
FRONTEND_DIR = os.getenv('FRONTEND_DIR', DEFAULT_FRONTEND_DIR)
HAS_FRONTEND_ASSETS = os.path.isdir(FRONTEND_DIR)
DEBUG_MODE = _env_bool('FLASK_DEBUG', False)
ENABLE_DEBUG_ROUTES = _env_bool('ENABLE_DEBUG_ROUTES', DEBUG_MODE)
PORT = _env_int('PORT', 5000)
MAX_UPLOAD_SIZE_BYTES = _env_int('MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
CORS_ALLOWED_ORIGINS = _env_csv('CORS_ALLOWED_ORIGINS')
DEFAULT_PROD_ORIGINS = [
    'https://app.alfagroups.tech',
    'https://web-production-4c3f2.up.railway.app',
    'https://smart-evidence-writer.vercel.app'
]
DEFAULT_DEV_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://localhost:5500',  # Live Server default
]
# In debug mode or if explicitly requested, allow * or more flexible origins
DEFAULT_ALLOWED_ORIGINS = DEFAULT_PROD_ORIGINS + DEFAULT_DEV_ORIGINS

app = Flask(__name__, static_folder=FRONTEND_DIR if HAS_FRONTEND_ASSETS else None)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_BYTES

# Robust CORS configuration for platform readiness
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Client-ID", "Authorization"],
            "expose_headers": ["Content-Disposition"]
        }
    },
)

# ─────────────────────────────────────────────────────────
# IN-MEMORY SESSION STORE
# ─────────────────────────────────────────────────────────
# Structure: sessions[session_id] = {
#   'file_bytes': bytes,
#   'filename': str,
#   'metadata': dict,
#   'frames': dict,
#   'analysis': dict,
#   'report': dict,
#   'pdf_bytes': bytes,
#   'status': str,  # 'uploaded' | 'analyzing' | 'complete' | 'error'
#   'progress': int,
#   'progress_message': str,
#   'created_at': float,
#   'error': str,
# }
sessions = {}
sessions_lock = threading.RLock() # Changed to RLock to prevent reentrancy deadlocks
SESSION_TTL = 30 * 60  # 30 minutes


def cleanup_expired_sessions():
    """Remove sessions older than TTL."""
    now = time.time()
    with sessions_lock:
        expired = [sid for sid, s in sessions.items() if now - s.get('created_at', 0) > SESSION_TTL]
        for sid in expired:
            del sessions[sid]
            logger.info(f"Cleaned up expired session: {sid}")


def start_cleanup_timer():
    """Run cleanup every 5 minutes."""
    cleanup_expired_sessions()
    timer = threading.Timer(300, start_cleanup_timer)
    timer.daemon = True
    timer.start()


start_cleanup_timer()


# ─────────────────────────────────────────────────────────
# IMPORTS — Local utils & Core Engine
# ─────────────────────────────────────────────────────────
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from backend.engine.media_processor import get_media_metadata
    from backend.reporting.pdf_generator import generate_pdf
    from backend.ai_providers.gemini import GeminiProvider
    from backend.engine.evidence_engine import EvidenceEngine
    from backend.utils.validation import validate_media_safety
except ModuleNotFoundError:
    from engine.media_processor import get_media_metadata
    from reporting.pdf_generator import generate_pdf
    from ai_providers.gemini import GeminiProvider
    from engine.evidence_engine import EvidenceEngine
    from utils.validation import validate_media_safety

# ─────────────────────────────────────────────────────────
# PLATFORM PROTECTION & USAGE TRACKING (In-Memory)
# ─────────────────────────────────────────────────────────
# In a production environment, use Redis for these.
usage_stats = defaultdict(lambda: {
    'hourly_count': 0,
    'daily_count': 0,
    'last_request_at': 0,
    'last_hour_reset': datetime.now().strftime('%Y-%m-%d-%H'),
    'last_day_reset': datetime.now().strftime('%Y-%m-%d'),
    'active_analyses': 0
})
ip_usage = defaultdict(lambda: {
    'hourly_count': 0,
    'daily_count': 0,
    'last_request_at': 0,
    'last_hour_reset': datetime.now().strftime('%Y-%m-%d-%H'),
    'last_day_reset': datetime.now().strftime('%Y-%m-%d'),
    'active_analyses': 0
})

PLATFORM_LIMITS = {
    'per_client_hourly_limit': _env_int('CLIENT_HOURLY_LIMIT', 1),
    'per_client_daily_limit': _env_int('CLIENT_DAILY_LIMIT', 3),
    'per_ip_hourly_limit': _env_int('IP_HOURLY_LIMIT', 3),
    'per_ip_daily_limit': _env_int('IP_DAILY_LIMIT', 12),
    'global_daily': _env_int('GLOBAL_DAILY_LIMIT', 200),
    'cooldown_seconds': _env_int_with_alias('RATE_LIMIT_COOLDOWN', 'REQUEST_COOLDOWN_SECONDS', 30),
    'max_concurrency_per_client': _env_int('MAX_CONCURRENCY_PER_CLIENT', 1),
    'max_concurrency_per_ip': _env_int('MAX_CONCURRENCY_PER_IP', 3),
    'max_video_duration': _env_int('MAX_VIDEO_DURATION', 60),  # seconds
    'max_file_size': MAX_UPLOAD_SIZE_BYTES,
    'min_resolution': (160, 160),
    'allowed_extensions': {'.mp4', '.mov', '.avi', '.jpg', '.jpeg', '.png', '.wav'}
}

global_stats = {
    'total_daily_count': 0,
    'last_reset': datetime.now().date()
}

tracker_lock = threading.Lock()

def check_limits(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_id = request.headers.get('X-Client-ID')
        ip = request.remote_addr
        now = time.time()
        today = datetime.now().date()
        if not client_id:
            return jsonify({'error': 'X-Client-ID header missing'}), 400

        with tracker_lock:
            # 1. Reset counters if needed (Global daily, per-client hourly/daily, per-IP hourly/daily)
            if global_stats['last_reset'] != today:
                global_stats['total_daily_count'] = 0
                global_stats['last_reset'] = today
            
            this_hour = datetime.now().strftime('%Y-%m-%d-%H')
            this_day = datetime.now().strftime('%Y-%m-%d')
            for storage in [usage_stats[client_id], ip_usage[ip]]:
                if storage.get('last_hour_reset') != this_hour:
                    storage['hourly_count'] = 0
                    storage['last_hour_reset'] = this_hour
                if storage.get('last_day_reset') != this_day:
                    storage['daily_count'] = 0
                    storage['last_day_reset'] = this_day

            # 2. Global Platform Quota
            if global_stats['total_daily_count'] >= PLATFORM_LIMITS['global_daily']:
                return jsonify({'error': 'Platform daily capacity reached. Try again tomorrow.'}), 503

            # 3. Cooldown check
            if now - usage_stats[client_id]['last_request_at'] < PLATFORM_LIMITS['cooldown_seconds']:
                wait = int(PLATFORM_LIMITS['cooldown_seconds'] - (now - usage_stats[client_id]['last_request_at']))
                return jsonify({'error': f'Request cooldown active. Wait {wait}s.'}), 429

            # 4. Hourly/Daily limits
            if usage_stats[client_id]['hourly_count'] >= PLATFORM_LIMITS['per_client_hourly_limit']:
                return jsonify({'error': 'Hourly analysis limit reached for this Client ID.'}), 429
            if usage_stats[client_id]['daily_count'] >= PLATFORM_LIMITS['per_client_daily_limit']:
                return jsonify({'error': 'Daily analysis limit reached for this Client ID.'}), 429
            if ip_usage[ip]['hourly_count'] >= PLATFORM_LIMITS['per_ip_hourly_limit']:
                return jsonify({'error': 'Hourly analysis limit reached for this IP.'}), 429
            if ip_usage[ip]['daily_count'] >= PLATFORM_LIMITS['per_ip_daily_limit']:
                return jsonify({'error': 'Daily analysis limit reached for this IP.'}), 429

            # 5. Concurrency check
            if usage_stats[client_id]['active_analyses'] >= PLATFORM_LIMITS['max_concurrency_per_client']:
                return jsonify({'error': 'Active analysis already in progress for this Client ID.'}), 429
            if ip_usage[ip]['active_analyses'] >= PLATFORM_LIMITS['max_concurrency_per_ip']:
                return jsonify({'error': 'Maximum concurrent analyses reached for this IP.'}), 429

        return f(*args, **kwargs)
    return decorated_function

# ═════════════════════════════════════════════════════════
# ROUTES — Static files
# ═════════════════════════════════════════════════════════

@app.route('/')
def serve_frontend():
    """Serve the main frontend page."""
    if not HAS_FRONTEND_ASSETS:
        return jsonify({
            'service': 'Alfa Hawk API',
            'status': 'online',
            'frontend': 'deployed separately',
        })
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """Serve static frontend assets."""
    if not HAS_FRONTEND_ASSETS:
        abort(404)
    return send_from_directory(FRONTEND_DIR, path)


# ═════════════════════════════════════════════════════════
# ROUTES — API
# ═════════════════════════════════════════════════════════

@app.route('/api/upload', methods=['POST'])
@check_limits
def upload_evidence():
    """
    Upload an evidence file. Stores in memory only.
    Includes launch-ready validation and platform tracking.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({'error': 'Empty file'}), 400

    # 1. Deep Validation
    valid, err_msg = validate_media_safety(file_bytes, file.filename, PLATFORM_LIMITS)
    if not valid:
        return jsonify({'error': err_msg}), 400

    # 2. Tracking Update (Tentative upload success)
    client_id = request.headers.get('X-Client-ID')
    ip = request.remote_addr
    with tracker_lock:
        usage_stats[client_id]['last_request_at'] = time.time()
        ip_usage[ip]['last_request_at'] = time.time()

    # 3. Create Session
    session_id = str(uuid.uuid4())
    filename = file.filename
    evidence_hash = hashlib.sha256(file_bytes).hexdigest()
    metadata = get_media_metadata(file_bytes, filename)
    metadata['evidence_sha256'] = evidence_hash

    # Optional BYO Key (format & live validation)
    byo_key = request.form.get('ai_api_key', '').strip()
    if byo_key:
        if not byo_key.startswith('AIza'):
            return jsonify({'error': 'Invalid Gemini API key format. Must start with "AIza".'}), 401
        
        # Live verification call (lightweight list models check)
        temp_provider = GeminiProvider(api_key=byo_key)
        if not temp_provider.verify_api_key(byo_key):
            return jsonify({'error': 'API Key verification failed. Please check your key or quota.'}), 401
        
        logger.info(f"Session {session_id} using verified BYO AI key.")

    case_info = {
        'case_number': request.form.get('case_number', ''),
        'officer_id': request.form.get('officer_id', ''),
        'case_description': request.form.get('case_description', ''),
        'byo_key': byo_key if byo_key else None
    }

    with sessions_lock:
        sessions[session_id] = {
            'file_bytes': file_bytes,
            'filename': filename,
            'metadata': metadata,
            'case_info': case_info,
            'frames': {},
            'analysis': None,
            'report': None,
            'pdf_bytes': None,
            'status': 'uploaded',
            'progress': 0,
            'progress_message': 'Evidence validated and staged in memory.',
            'created_at': time.time(),
            'error': None,
            'tracking': {'client_id': client_id, 'ip': ip}
        }

    # Operational mask logging
    masked_key = (f"{byo_key[:4]}...{byo_key[-4:]}") if byo_key else "None"
    logger.info(f"Upload: CID={client_id[:8]}... IP={ip} BYO_KEY={masked_key}")

    return jsonify({
        'session_id': session_id,
        'metadata': metadata,
        'mode': 'BYO Key' if byo_key else 'Platform AI',
        'message': 'Evidence validated and staged in memory.',
    })


@app.route('/api/analyze/<session_id>', methods=['POST'])
def analyze_evidence_route(session_id):
    """
    Start the full analysis pipeline using EvidenceEngine.
    """
    client_id = request.headers.get('X-Client-ID')
    ip = request.remote_addr

    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
        if session['status'] == 'analyzing':
            return jsonify({'error': 'Analysis already in progress'}), 409
        if session.get('metadata', {}).get('media_type') == 'audio':
            return jsonify({'error': 'WAV upload is accepted for validation, but AI analysis is not available for audio evidence in v1.0.0.'}), 400

        # Update counters
        with tracker_lock:
            usage_stats[client_id]['hourly_count'] += 1
            usage_stats[client_id]['daily_count'] += 1
            ip_usage[ip]['hourly_count'] += 1
            ip_usage[ip]['daily_count'] += 1
            usage_stats[client_id]['active_analyses'] += 1
            ip_usage[ip]['active_analyses'] += 1
            global_stats['total_daily_count'] += 1

        session['status'] = 'analyzing'
        session['progress'] = 5
        session['progress_message'] = 'Initializing Open Source Evidence Engine...'
        session['tracking'] = {'client_id': client_id, 'ip': ip}

    # Run analysis in background thread
    thread = threading.Thread(target=_run_analysis_pipeline, args=(session_id,))
    thread.daemon = True
    thread.start()

    return jsonify({
        'session_id': session_id,
        'status': 'analyzing',
        'message': 'Analysis started.',
    })


@app.route('/api/status/<session_id>')
def get_status(session_id):
    """Get current analysis status and progress."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404

        response = {
            'session_id': session_id,
            'status': session['status'],
            'progress': session['progress'],
            'progress_message': session['progress_message'],
            'metadata': session['metadata'],
        }

        if session['status'] == 'error':
            response['error'] = session.get('error', 'Unknown error')

        if session['status'] == 'complete':
            response['has_report'] = session['report'] is not None
            response['has_pdf'] = session['pdf_bytes'] is not None
            response['report'] = session.get('report')

        return jsonify(response)


@app.route('/api/report/<session_id>')
def get_report(session_id):
    """Get the structured report JSON."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
        if session['status'] != 'complete':
            return jsonify({'error': 'Analysis not yet complete'}), 400

        return jsonify({
            'session_id': session_id,
            'report': session['report'],
        })


@app.route('/api/pdf/<session_id>')
def download_pdf(session_id):
    """Download the generated PDF report."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
        if not session.get('pdf_bytes'):
            return jsonify({'error': 'PDF not yet generated'}), 400

        pdf_bytes = session['pdf_bytes']
        case_num = session.get('report', {}).get('header', {}).get('case_number', 'report')

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename=Evidence_Report_{case_num}.pdf',
            'Content-Length': str(len(pdf_bytes)),
        }
    )


@app.route('/api/frames/<session_id>/<frame_id>')
def get_frame(session_id, frame_id):
    """Serve a specific extracted frame image from memory."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        frames = session.get('frames', {})
        frame = frames.get(frame_id)
        if not frame:
            return jsonify({'error': 'Frame not found'}), 404

        img_bytes = frame.get('image_bytes')
        if not img_bytes:
            return jsonify({'error': 'Frame data not available'}), 404

    return Response(
        img_bytes,
        mimetype='image/jpeg',
        headers={'Content-Length': str(len(img_bytes))}
    )


@app.route('/api/frames/<session_id>')
def list_frames(session_id):
    """List all extracted frames for a session."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        frames = session.get('frames', {})
        frame_list = []
        for fid, fdata in frames.items():
            frame_list.append({
                'frame_id': fid,
                'timestamp': fdata.get('timestamp', 0),
                'timestamp_formatted': fdata.get('timestamp_formatted', ''),
                'description': fdata.get('description', ''),
                'url': f'/api/frames/{session_id}/{fid}',
            })

    return jsonify({'session_id': session_id, 'frames': frame_list})


@app.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Manually delete a session and free memory."""
    with sessions_lock:
        if session_id in sessions:
            del sessions[session_id]
            return jsonify({'message': 'Session cleaned up'})
        return jsonify({'error': 'Session not found'}), 404


@app.route('/api/usage')
def get_usage_stats():
    """Get usage stats for the current client."""
    client_id = request.headers.get('X-Client-ID')
    ip = request.remote_addr
    
    if not client_id:
        return jsonify({'error': 'X-Client-ID header missing'}), 400

    with tracker_lock:
        client_stats = usage_stats[client_id]
        ip_stats = ip_usage[ip]
        
        return jsonify({
            'client_hourly_count': client_stats.get('hourly_count', 0),
            'client_hourly_limit': PLATFORM_LIMITS['per_client_hourly_limit'],
            'client_daily_count': client_stats.get('daily_count', 0),
            'client_daily_limit': PLATFORM_LIMITS['per_client_daily_limit'],
            'ip_hourly_count': ip_stats.get('hourly_count', 0),
            'ip_hourly_limit': PLATFORM_LIMITS['per_ip_hourly_limit'],
            'ip_daily_count': ip_stats.get('daily_count', 0),
            'ip_daily_limit': PLATFORM_LIMITS['per_ip_daily_limit'],
            'global_daily_count': global_stats['total_daily_count'],
            'global_daily_limit': PLATFORM_LIMITS['global_daily']
        })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ai_configured': bool(os.getenv('GEMINI_API_KEY')),
        'active_sessions': len(sessions),
        'storage': 'in-memory only',
        'debug_routes_enabled': ENABLE_DEBUG_ROUTES,
    })


@app.route('/api/debug/sessions')
def debug_sessions():
    """Debug route to check internal session states."""
    if not ENABLE_DEBUG_ROUTES:
        abort(404)
    with sessions_lock:
        return jsonify({sid: {
            'status': s['status'],
            'progress': s['progress'],
            'msg': s['progress_message'],
            'has_report': s['report'] is not None,
            'has_pdf': s['pdf_bytes'] is not None
        } for sid, s in sessions.items()})


# ═════════════════════════════════════════════════════════
# ANALYSIS PIPELINE (runs in background thread)
# ═════════════════════════════════════════════════════════

def _run_analysis_pipeline(session_id):
    """
    Optimized V2.1 Pipeline using EvidenceEngine and abstracted providers.
    """
    client_id = None
    ip = None
    try:
        with sessions_lock:
            session = sessions.get(session_id)
            if not session: return
            file_bytes = session['file_bytes']
            filename = session['filename']
            case_info = session['case_info']
            client_id = session['tracking']['client_id']
            ip = session['tracking']['ip']

        # 1. Setup Engine with abstracted provider
        provider_key = case_info.get('byo_key') or os.getenv('GEMINI_API_KEY')
        provider = GeminiProvider(api_key=provider_key)
        engine = EvidenceEngine(ai_provider=provider)

        def progress_cb(p, m):
            _update_progress(session_id, p, m)

        # 2. Run Engine (Open Source Core logic) with 90s timeout
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                engine.run_analysis,
                file_bytes=file_bytes,
                filename=filename,
                case_data=case_info,
                api_key=provider_key,
                progress_callback=progress_cb
            )
            try:
                report = future.result(timeout=180) # Increased to 180s for Native Video API
            except concurrent.futures.TimeoutError:
                logger.error(f"Analysis Timeout {session_id}")
                raise Exception("AI analysis timed out (180s limit reached). The evidence may be too complex or the provider is slow.")

        # 3. Finalize
        # Note: Generate PDF outside the lock to avoid blocking other requests
        _update_progress(session_id, 90, 'Applying platform branding and generating PDF...')
        try:
            pdf_bytes = generate_pdf(report)
        except Exception as pdf_err:
            logger.error(f"PDF Generation failed for {session_id}: {pdf_err}")
            pdf_bytes = None

        with sessions_lock:
            if session_id in sessions:
                # Store report and PDF
                sessions[session_id]['report'] = report
                sessions[session_id]['pdf_bytes'] = pdf_bytes
                
                sessions[session_id]['file_bytes'] = None # Done with raw bytes
                sessions[session_id]['status'] = 'complete'
                sessions[session_id]['progress'] = 100
                sessions[session_id]['progress_message'] = 'Forensic report generated successfully.'

    except Exception as e:
        logger.error(f"Engine Failure {session_id}: {str(e)}")
        # Mask potentially sensitive error details
        clean_msg = str(e)
        if "API_KEY" in clean_msg.upper() or "AIza" in clean_msg:
            clean_msg = "AI Provider authentication error. Please check your API key."
        
        with sessions_lock:
            if session_id in sessions:
                sessions[session_id]['status'] = 'error'
                sessions[session_id]['error'] = clean_msg
                sessions[session_id]['progress_message'] = f'Error: {clean_msg}'
    finally:
        # Decrement concurrency counters
        if client_id and ip:
            with tracker_lock:
                usage_stats[client_id]['active_analyses'] = max(0, usage_stats[client_id]['active_analyses'] - 1)
                ip_usage[ip]['active_analyses'] = max(0, ip_usage[ip]['active_analyses'] - 1)
        
        logger.info(f"Analysis pipeline complete for session: {session_id}")


def _update_progress(session_id, progress, message):
    """Update session progress."""
    with sessions_lock:
        if session_id in sessions:
            sessions[session_id]['progress'] = progress
            sessions[session_id]['progress_message'] = message
    logger.info(f"[{session_id[:8]}] {progress}% — {message}")


# ═════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("  Alfa Hawk — Starting...")
    logger.info("  Developed by Alfa Labs | A Product of Alfa Groups")
    logger.info("  Storage: IN-MEMORY ONLY (no file persistence)")
    logger.info(f"  Frontend: {FRONTEND_DIR}")
    logger.info("=" * 60)
    logger.info("  Debug mode: %s", "enabled" if DEBUG_MODE else "disabled")
    logger.info("  API origins: %s", ", ".join(CORS_ALLOWED_ORIGINS or DEFAULT_ALLOWED_ORIGINS))
    app.run(host='0.0.0.0', debug=DEBUG_MODE, port=PORT, threaded=True)
