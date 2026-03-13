# utils/report_builder.py — Structured police/legal report builder
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


def build_structured_report(analysis, metadata, frames=None, case_info=None):
    """
    Build a structured evidence report in police/legal format.

    Args:
        analysis: dict from ai_analyzer (structured JSON findings)
        metadata: dict from media_processor (file metadata)
        frames: dict of extracted frames {frame_id: {base64, timestamp, ...}}
        case_info: dict with optional case_number, officer_id, case_description

    Returns:
        dict — full structured report ready for PDF generation
    """
    case_info = case_info or {}
    frames = frames or {}

    report = {
        'header': _build_header(case_info),
        'evidence_description': _build_evidence_description(metadata),
        'executive_summary': analysis.get('executive_summary', 'No summary available.'),
        'scene_description': analysis.get('scene_description', 'No scene description available.'),
        'detailed_analysis': _build_detailed_analysis(analysis),
        'violations': _build_violations_section(analysis.get('violations', []), frames),
        'accidents': _build_accidents_section(analysis.get('accidents', []), frames),
        'persons_identified': _build_persons_section(analysis.get('human_faces', []), frames),
        'vehicle_registry': _build_vehicle_registry(analysis.get('number_plates', []), frames),
        'landmarks_locations': _build_landmarks_section(analysis.get('landmarks', [])),
        'objects_of_interest': analysis.get('objects_of_interest', []),
        'timeline': _build_timeline(analysis),
        'environmental_conditions': analysis.get('environmental_conditions', {}),
        'forensic_observations': analysis.get('forensic_observations', ''),
        'risk_assessment': analysis.get('risk_assessment', {}),
        'investigative_recommendations': analysis.get('investigative_recommendations', []),
        'evidence_exhibits': _build_exhibits(frames, analysis),
        'certification': _build_certification(),
        'confidence_score': analysis.get('confidence_score', 0),
        'analysis_notes': analysis.get('analysis_notes', ''),
        'generated_at': datetime.now().isoformat(),
    }

    return report


# ─────────────────────────────────────────────────────────
# SECTION BUILDERS
# ─────────────────────────────────────────────────────────

def _build_header(case_info):
    """Build report header with case information."""
    return {
        'report_title': 'EVIDENCE ANALYSIS REPORT',
        'system_name': 'Alfa Hawk — AI Evidence Analysis Platform | Alfa Labs',
        'classification': 'RESTRICTED — FOR OFFICIAL USE ONLY',
        'case_number': case_info.get('case_number', f'AH-{datetime.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'),
        'report_id': f'RPT-{str(uuid.uuid4())[:8].upper()}',
        'date': datetime.now().strftime('%d %B %Y'),
        'time': datetime.now().strftime('%H:%M:%S IST'),
        'officer_id': case_info.get('officer_id', 'Not Specified'),
        'case_description': case_info.get('case_description', 'Evidence submitted for AI-assisted analysis'),
    }


def _build_evidence_description(metadata):
    """Build evidence file description section."""
    desc = {
        'filename': metadata.get('filename', 'Unknown'),
        'media_type': metadata.get('media_type', 'Unknown'),
        'mime_type': metadata.get('mime_type', 'Unknown'),
        'file_size': f"{metadata.get('file_size_mb', 0)} MB",
        'upload_timestamp': metadata.get('upload_timestamp', ''),
    }

    # Add media-specific details
    if metadata.get('width') and metadata.get('height'):
        desc['dimensions'] = f"{metadata['width']} × {metadata['height']} pixels"
    if metadata.get('duration_seconds'):
        mins = int(metadata['duration_seconds'] // 60)
        secs = int(metadata['duration_seconds'] % 60)
        desc['duration'] = f"{mins}m {secs}s"
    if metadata.get('fps'):
        desc['frame_rate'] = f"{metadata['fps']} FPS"
    if metadata.get('format'):
        desc['format'] = metadata['format']

    return desc


def _build_detailed_analysis(analysis):
    """Build the detailed analysis section."""
    sections = []

    if analysis.get('scene_description'):
        sections.append({
            'title': 'Scene Overview',
            'content': analysis['scene_description']
        })

    if analysis.get('forensic_observations'):
        sections.append({
            'title': 'Forensic Observations',
            'content': analysis['forensic_observations']
        })

    if analysis.get('analysis_notes'):
        sections.append({
            'title': 'Analyst Notes',
            'content': analysis['analysis_notes']
        })

    # Audio-specific
    if analysis.get('transcript_summary'):
        sections.append({
            'title': 'Audio Transcript Summary',
            'content': analysis['transcript_summary']
        })

    if analysis.get('transcript'):
        sections.append({
            'title': 'Full Audio Transcript',
            'content': analysis['transcript']
        })

    if analysis.get('emotional_tone'):
        sections.append({
            'title': 'Emotional Tone Analysis',
            'content': analysis['emotional_tone']
        })

    return sections


def _build_violations_section(violations, frames):
    """Build violations section with linked evidence frames."""
    enriched = []
    for i, v in enumerate(violations):
        entry = {
            'index': i + 1,
            'type': v.get('type', 'Unknown'),
            'description': v.get('description', 'No description'),
            'severity': v.get('severity', 'Unknown'),
            'evidence_details': v.get('evidence_details', ''),
            'detected_at': v.get('detected_at_timestamp', ''),
        }
        # Link to frame if available
        frame_id = v.get('frame_id')
        if frame_id and frame_id in frames:
            entry['evidence_frame_base64'] = frames[frame_id].get('base64', '')
            entry['evidence_frame_timestamp'] = frames[frame_id].get('timestamp_formatted', '')
        enriched.append(entry)
    return enriched


def _build_accidents_section(accidents, frames):
    """Build accidents section with severity and damage assessment."""
    enriched = []
    for i, a in enumerate(accidents):
        entry = {
            'index': i + 1,
            'type': a.get('type', 'Unknown'),
            'description': a.get('description', 'No description'),
            'severity': a.get('severity', 'Unknown'),
            'vehicles_involved': a.get('vehicles_involved', 'Unknown'),
            'damage_assessment': a.get('damage_assessment', 'Not assessed'),
            'detected_at': a.get('detected_at_timestamp', ''),
        }
        frame_id = a.get('frame_id')
        if frame_id and frame_id in frames:
            entry['evidence_frame_base64'] = frames[frame_id].get('base64', '')
        enriched.append(entry)
    return enriched


def _build_persons_section(faces, frames):
    """Build identified persons section."""
    enriched = []
    for i, f in enumerate(faces):
        entry = {
            'index': i + 1,
            'person_id': f.get('person_id', f'Person {i + 1}'),
            'description': f.get('description', 'No description'),
            'position': f.get('position_in_frame', ''),
            'activity': f.get('activity', ''),
            'relevance': f.get('relevance', 'Unknown'),
            'detected_at': f.get('detected_at_timestamp', ''),
        }
        frame_id = f.get('frame_id')
        if frame_id and frame_id in frames:
            entry['evidence_frame_base64'] = frames[frame_id].get('base64', '')
        enriched.append(entry)
    return enriched


def _build_vehicle_registry(plates, frames):
    """Build vehicle/number plate registry."""
    enriched = []
    for i, p in enumerate(plates):
        entry = {
            'index': i + 1,
            'plate_text': p.get('plate_text', 'Unreadable'),
            'vehicle_type': p.get('vehicle_type', 'Unknown'),
            'vehicle_color': p.get('vehicle_color', 'Unknown'),
            'plate_region': p.get('plate_region', 'Unknown'),
            'confidence': p.get('confidence', 'Unknown'),
            'detected_at': p.get('detected_at_timestamp', ''),
        }
        frame_id = p.get('frame_id')
        if frame_id and frame_id in frames:
            entry['evidence_frame_base64'] = frames[frame_id].get('base64', '')
        enriched.append(entry)
    return enriched


def _build_landmarks_section(landmarks):
    """Build landmarks and locations section."""
    enriched = []
    for i, l in enumerate(landmarks):
        enriched.append({
            'index': i + 1,
            'name': l.get('name', 'Unknown'),
            'type': l.get('type', 'Unknown'),
            'details': l.get('details', ''),
            'location_hint': l.get('location_hint', ''),
            'detected_at': l.get('detected_at_timestamp', ''),
        })
    return enriched


def _build_timeline(analysis):
    """Build chronological timeline of events."""
    events = analysis.get('timeline_events', [])
    timeline = []
    for i, e in enumerate(events):
        timeline.append({
            'sequence': i + 1,
            'time': e.get('time_indicator', f'Event {i + 1}'),
            'event': e.get('event', 'No description'),
        })
    return timeline


def _build_exhibits(frames, analysis):
    """Build evidence exhibits gallery with analyzed frames."""
    exhibits = []

    # Get frame IDs that are linked to findings
    finding_frames = set()
    for section in ['violations', 'accidents', 'number_plates', 'human_faces']:
        for item in analysis.get(section, []):
            fid = item.get('frame_id')
            if fid:
                finding_frames.add(fid)

    # Add frames linked to specific findings first
    for frame_id in finding_frames:
        if frame_id in frames:
            frame = frames[frame_id]
            exhibits.append({
                'frame_id': frame_id,
                'base64': frame.get('base64', ''),
                'timestamp': frame.get('timestamp_formatted', '00:00:00'),
                'description': frame.get('description', ''),
                'is_key_finding': True,
            })

    # Add remaining key frames
    for frame_id, frame in frames.items():
        if frame_id not in finding_frames:
            exhibits.append({
                'frame_id': frame_id,
                'base64': frame.get('base64', ''),
                'timestamp': frame.get('timestamp_formatted', '00:00:00'),
                'description': frame.get('description', ''),
                'is_key_finding': False,
            })

    return exhibits


def _build_certification():
    """Build report certification / disclaimer section."""
    return {
        'disclaimer': 'This report has been generated by an automated AI-powered evidence analysis system. '
                       'All findings should be independently verified by qualified investigating officers '
                       'before being used in legal proceedings.',
        'system': 'Alfa Hawk — AI Evidence Analysis Platform | Alfa Labs',
        'generated_at': datetime.now().strftime('%d %B %Y, %H:%M:%S IST'),
        'signature_blocks': [
            {
                'title': 'Investigating Officer',
                'name': '___________________________',
                'rank': '___________________________',
                'badge': '___________________________',
                'date': '___________________________',
            },
            {
                'title': 'Reviewing Officer',
                'name': '___________________________',
                'rank': '___________________________',
                'badge': '___________________________',
                'date': '___________________________',
            }
        ]
    }
