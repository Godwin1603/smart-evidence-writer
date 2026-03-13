# app.py — Alfa Hawk: Flask backend with in-memory storage
import os
import sys
import io
import uuid
import time
import logging
import threading
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB
CORS(app)

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
sessions_lock = threading.Lock()
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
# IMPORTS — Local utils
# ─────────────────────────────────────────────────────────
sys.path.append(BASE_DIR)

from utils.media_processor import get_media_type, get_media_metadata, process_image, process_audio
from utils.frame_extractor import extract_key_frames, extract_scene_change_frames, image_to_frame_entry
from utils.ai_analyzer import analyze_image, analyze_video, analyze_video_frames, analyze_audio, is_gemini_available
from utils.aws_analyzer import analyze_video_aws, is_aws_configured
from utils.report_builder import build_structured_report
from utils.pdf_generator import generate_pdf


# ═════════════════════════════════════════════════════════
# ROUTES — Static files
# ═════════════════════════════════════════════════════════

@app.route('/')
def serve_frontend():
    """Serve the main frontend page."""
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """Serve static frontend assets."""
    return send_from_directory(FRONTEND_DIR, path)


# ═════════════════════════════════════════════════════════
# ROUTES — API
# ═════════════════════════════════════════════════════════

@app.route('/api/upload', methods=['POST'])
def upload_evidence():
    """
    Upload an evidence file. Stores in memory only.
    Returns a session_id for subsequent operations.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Read file into memory
    file_bytes = file.read()
    if len(file_bytes) == 0:
        return jsonify({'error': 'Empty file'}), 400

    filename = file.filename

    # Get metadata
    metadata = get_media_metadata(file_bytes, filename)

    # Create session
    session_id = str(uuid.uuid4())

    # Get optional case info from form
    case_info = {
        'case_number': request.form.get('case_number', ''),
        'officer_id': request.form.get('officer_id', ''),
        'case_description': request.form.get('case_description', ''),
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
            'progress_message': 'File uploaded successfully',
            'created_at': time.time(),
            'error': None,
        }

    logger.info(f"File uploaded: {filename} ({metadata['file_size_mb']} MB) → Session: {session_id}")

    return jsonify({
        'session_id': session_id,
        'metadata': metadata,
        'message': 'File uploaded to memory. Ready for analysis.',
    })


@app.route('/api/analyze/<session_id>', methods=['POST'])
def analyze_evidence_route(session_id):
    """
    Start the full analysis pipeline for an uploaded file.
    Runs asynchronously and updates session progress.
    """
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
        if session['status'] == 'analyzing':
            return jsonify({'error': 'Analysis already in progress'}), 409

        session['status'] = 'analyzing'
        session['progress'] = 5
        session['progress_message'] = 'Starting analysis pipeline...'

    # Run analysis in background thread
    thread = threading.Thread(target=_run_analysis_pipeline, args=(session_id,))
    thread.daemon = True
    thread.start()

    return jsonify({
        'session_id': session_id,
        'status': 'analyzing',
        'message': 'Analysis started. Poll /api/status/<session_id> for progress.',
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


@app.route('/health')
def health_check():
    """Health check endpoint."""
    from config import GROQ_API_KEY
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ai_configured': bool(GROQ_API_KEY and GROQ_API_KEY != 'your_groq_api_key_here'),
        'active_sessions': len(sessions),
        'storage': 'in-memory only',
    })


# ═════════════════════════════════════════════════════════
# ANALYSIS PIPELINE (runs in background thread)
# ═════════════════════════════════════════════════════════

def _run_analysis_pipeline(session_id):
    """
    Full analysis pipeline:
    1. Process media (extract frames / transcribe audio)
    2. AI analysis of each frame/transcript
    3. Build structured report
    4. Generate PDF
    """
    try:
        with sessions_lock:
            session = sessions.get(session_id)
            if not session:
                return

        file_bytes = session['file_bytes']
        filename = session['filename']
        metadata = session['metadata']
        media_type = metadata.get('media_type', 'unknown')

        # ──── STEP 1: Process media ────
        _update_progress(session_id, 10, 'Processing media file...')

        frames = {}
        transcript = None

        if media_type == 'image':
            _update_progress(session_id, 15, 'Preparing image for analysis...')
            processed_bytes, b64 = process_image(file_bytes)
            frames = image_to_frame_entry(file_bytes, filename)

        elif media_type == 'video':
            if is_aws_configured():
                _update_progress(session_id, 15, 'AWS configured. Extracting high-density frames for secondary AI vision analysis...')
                # Extract high density frames (every 0.5s) so Gemini doesn't miss split-second details
                frames = extract_key_frames(file_bytes, max_frames=50, interval_seconds=0.5, original_filename=filename)
                scene_frames = extract_scene_change_frames(file_bytes, original_filename=filename)
                frames.update(scene_frames)
                _update_progress(session_id, 20, f'{len(frames)} total frames extracted for Gemini Vision.')
            else:
                # Fallback to local high-density frame extraction (1-second intervals for forensic detail)
                _update_progress(session_id, 15, 'Extracting high-density key frames from video...')
                frames = extract_key_frames(file_bytes, original_filename=filename)
                _update_progress(session_id, 25, f'Extracted {len(frames)} key frames. Detecting scene changes...')
    
                scene_frames = extract_scene_change_frames(file_bytes, original_filename=filename)
                frames.update(scene_frames)
                _update_progress(session_id, 30, f'Total {len(frames)} frames extracted.')

        elif media_type == 'audio':
            _update_progress(session_id, 15, 'Transcribing audio...')
            transcript = process_audio(file_bytes, filename)
            _update_progress(session_id, 30, 'Audio transcribed successfully.')

        else:
            _update_progress(session_id, 15, 'Unknown media type — attempting image analysis...')
            frames = image_to_frame_entry(file_bytes, filename)

        # Store frames in session
        with sessions_lock:
            if session_id in sessions:
                sessions[session_id]['frames'] = frames

        # ──── STEP 2: AI Analysis ────
        _update_progress(session_id, 35, 'Running AI analysis...')

        analysis = {}

        if media_type == 'image':
            _update_progress(session_id, 40, 'Analyzing image with AI vision model...')
            # Get the single frame's base64
            frame_data = list(frames.values())[0] if frames else None
            if frame_data:
                analysis = analyze_image(frame_data['base64'], metadata)
                # Link frame_id to analysis findings
                frame_id = list(frames.keys())[0]
                for section in ['violations', 'accidents', 'number_plates', 'human_faces']:
                    for item in analysis.get(section, []):
                        item['frame_id'] = frame_id
            _update_progress(session_id, 70, 'Image analysis complete.')

        elif media_type == 'video':
            if is_aws_configured():
                _update_progress(session_id, 35, 'Delegating deep forensic analysis to AWS Rekognition...')
                
                # Pass a callback to update progress through the stages in aws_analyzer
                def aws_progress_cb(prog, msg):
                    _update_progress(session_id, prog, msg)
                    
                analysis = analyze_video_aws(file_bytes, filename, metadata, frames=frames, progress_callback=aws_progress_cb)
                _update_progress(session_id, 70, 'AWS + Gemini Multimodal Video analysis complete.')
            else:
                # Fallback: Analyze frames (uses multi-frame context with Local OCR assistance)
                total_frames = len(frames)
                _update_progress(session_id, 40, f'Analyzing {total_frames} video frames locally with AI & Local OCR...')
                
                # Use top 30 frames for high detail coverage
                frames_to_analyze = dict(list(frames.items())[:30])
                analysis = analyze_video_frames(frames_to_analyze, metadata)
                _update_progress(session_id, 70, 'Video frame analysis complete.')

        elif media_type == 'audio':
            _update_progress(session_id, 40, 'Analyzing audio transcript with AI...')
            analysis = analyze_audio(transcript, metadata)
            _update_progress(session_id, 70, 'Audio analysis complete.')

        else:
            analysis = {
                'executive_summary': 'Unsupported media type — manual review required.',
                'violations': [], 'accidents': [], 'number_plates': [],
                'human_faces': [], 'landmarks': [],
            }

        with sessions_lock:
            if session_id in sessions:
                sessions[session_id]['analysis'] = analysis

        # ──── STEP 3: Build structured report ────
        _update_progress(session_id, 75, 'Building structured evidence report...')

        case_info = session.get('case_info', {})
        report = build_structured_report(analysis, metadata, frames, case_info)

        with sessions_lock:
            if session_id in sessions:
                sessions[session_id]['report'] = report

        # ──── STEP 4: Generate PDF ────
        _update_progress(session_id, 85, 'Generating PDF report...')

        pdf_bytes = generate_pdf(report)

        with sessions_lock:
            if session_id in sessions:
                sessions[session_id]['pdf_bytes'] = pdf_bytes

        # ──── STEP 5: Clean up file bytes to save memory ────
        _update_progress(session_id, 95, 'Finalizing report...')

        with sessions_lock:
            if session_id in sessions:
                # Remove raw file bytes to free memory (keep frames and report)
                sessions[session_id]['file_bytes'] = None
                sessions[session_id]['status'] = 'complete'
                sessions[session_id]['progress'] = 100
                sessions[session_id]['progress_message'] = 'Analysis complete! Report ready for download.'

        logger.info(f"Analysis pipeline complete for session: {session_id}")

    except Exception as e:
        logger.error(f"Analysis pipeline failed for {session_id}: {e}", exc_info=True)
        with sessions_lock:
            if session_id in sessions:
                sessions[session_id]['status'] = 'error'
                sessions[session_id]['error'] = str(e)
                sessions[session_id]['progress_message'] = f'Error: {str(e)}'


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
    app.run(debug=True, port=5000, threaded=True)