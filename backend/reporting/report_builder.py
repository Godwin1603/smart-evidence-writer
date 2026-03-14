# utils/report_builder.py — V2 Structured forensic evidence report builder (India Edition)
import logging
from datetime import datetime
import uuid

try:
    from backend.reporting.hash_utils import (
        PLATFORM_IDENTIFIER,
        PLATFORM_NAME,
        PLATFORM_VERSION,
        compute_report_integrity_hash,
    )
except ModuleNotFoundError:
    from reporting.hash_utils import (
        PLATFORM_IDENTIFIER,
        PLATFORM_NAME,
        PLATFORM_VERSION,
        compute_report_integrity_hash,
    )

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# IPC MAPPING TABLE — Backend-side static mapping
# Gemini outputs events, this table maps events → IPC law
# ─────────────────────────────────────────────────────────
IPC_MAPPING_TABLE = {
    'physical assault': {'section': 'IPC Section 351', 'description': 'Assault', 'category': 'criminal'},
    'assault': {'section': 'IPC Section 351', 'description': 'Assault', 'category': 'criminal'},
    'attempt to cause injury': {'section': 'IPC Section 324', 'description': 'Voluntarily causing hurt by dangerous weapons', 'category': 'criminal'},
    'causing hurt': {'section': 'IPC Section 323', 'description': 'Voluntarily causing hurt', 'category': 'criminal'},
    'grievous hurt': {'section': 'IPC Section 325', 'description': 'Voluntarily causing grievous hurt', 'category': 'criminal'},
    'firearm possession': {'section': 'Arms Act Section 25', 'description': 'Possession of prohibited arms', 'category': 'arms'},
    'weapon use': {'section': 'Arms Act Section 27', 'description': 'Use of arms', 'category': 'arms'},
    'rash driving': {'section': 'IPC Section 279', 'description': 'Rash driving or riding on a public way', 'category': 'traffic'},
    'reckless driving': {'section': 'IPC Section 279', 'description': 'Rash driving or riding on a public way', 'category': 'traffic'},
    'causing death by negligence': {'section': 'IPC Section 304A', 'description': 'Causing death by negligence', 'category': 'criminal'},
    'vehicle collision': {'section': 'IPC Section 279', 'description': 'Rash driving on a public way', 'category': 'traffic'},
    'hit and run': {'section': 'IPC Section 304A / MV Act Section 161', 'description': 'Causing death by negligence / Hit and run', 'category': 'traffic'},
    'mischief by fire': {'section': 'IPC Section 435', 'description': 'Mischief by fire or explosive substance', 'category': 'criminal'},
    'theft': {'section': 'IPC Section 378', 'description': 'Theft', 'category': 'criminal'},
    'robbery': {'section': 'IPC Section 390', 'description': 'Robbery', 'category': 'criminal'},
    'rioting': {'section': 'IPC Section 146', 'description': 'Rioting', 'category': 'criminal'},
    'unlawful assembly': {'section': 'IPC Section 141', 'description': 'Unlawful assembly', 'category': 'criminal'},
    'trespassing': {'section': 'IPC Section 441', 'description': 'Criminal trespass', 'category': 'criminal'},
    'signal violation': {'section': 'MV Act Section 119', 'description': 'Disobedience of traffic signs', 'category': 'traffic'},
    'no helmet': {'section': 'MV Act Section 129', 'description': 'Wearing of protective headgear', 'category': 'traffic'},
    'no seatbelt': {'section': 'MV Act Section 138', 'description': 'Safety measures for drivers and passengers', 'category': 'traffic'},
    'drunk driving': {'section': 'MV Act Section 185', 'description': 'Driving by a drunken person', 'category': 'traffic'},
    'wrong side driving': {'section': 'MV Act Section 119', 'description': 'Driving on wrong side', 'category': 'traffic'},
}

# Confidence level → percentage conversion
CONFIDENCE_LEVEL_MAP = {
    'low': 60,
    'medium': 75,
    'high': 90,
}


def build_forensic_report(raw_analysis, metadata, frames=None, case_data=None, engine_version="1.0"):
    """
    V2: Build a professional forensic evidence report.
    Args:
        raw_analysis: dict from provider (validated)
        metadata: dict from media_processor
        frames: dict of extracted frames
        case_data: dict with case details
        engine_version: string
    """
    case_info = case_data or {}
    frames = frames or {}
    # V4.0 Precision Data Mapping
    # Create a lookup map: "F1" -> UUID, "F2" -> UUID, etc.
    frame_map = {f"F{i+1}": fid for i, fid in enumerate(frames.keys())}
    # Also support reverse and direct UUID lookup
    for fid in frames.keys():
        frame_map[fid] = fid

    report = {
        # ── Header & Evidence Description ──
        'header': _build_header(case_info),
        'evidence_description': _build_evidence_description(metadata),
        'ai_metadata': {
            'model': 'Gemini 2.5 Flash',
            'engine_version': engine_version,
            'schema_version': '1.0'
        },

        # ── V2: Evidence Integrity ──
        'evidence_integrity': _build_evidence_integrity(metadata),

        # ── Executive Summary & Scene ──
        'executive_summary': raw_analysis.get('executive_summary', 'No summary available.'),
        'key_evidence_observations': raw_analysis.get('key_evidence_observations', []),
        'scene_description': _build_scene_description(raw_analysis.get('scene_description', {})),

        # ── V2.1: Video Quality Assessment ──
        'video_quality_assessment': _build_video_quality_assessment(raw_analysis.get('video_quality_assessment', {})),

        # ── V2: Incident Reconstruction ──
        'incident_phases': _build_incident_phases(raw_analysis.get('incident_phases', []), frame_map),

        # ── V2: Person Registry (P-ID system) ──
        'persons_identified': _build_person_registry(raw_analysis.get('persons', raw_analysis.get('human_faces', [])), frames, frame_map),

        # ── V2: Weapons & Objects of Interest ──
        'weapons_objects': _build_weapons_objects(raw_analysis.get('weapons_objects', raw_analysis.get('objects_of_interest', []))),

        # ── V2: Legal Classification (backend IPC mapping) ──
        'legal_classification': _build_legal_classification(raw_analysis),

        # ── Detailed Analysis (legacy, still included) ──
        'detailed_analysis': _build_detailed_analysis(raw_analysis),

        # ── Violations & Accidents ──
        'violations': _build_violations_section(raw_analysis.get('violations', []), frames),
        'accidents': _build_accidents_section(raw_analysis.get('accidents', []), frames),

        # ── Vehicle Registry ──
        'vehicle_registry': _build_vehicle_registry(raw_analysis.get('number_plates', []), frames),

        # ── Timeline ──
        'timeline': _build_timeline(raw_analysis, frame_map),

        # ── Landmarks ──
        'landmarks_locations': _build_landmarks_section(raw_analysis.get('landmarks', [])),

        # ── Risk Assessment ──
        'risk_assessment': _build_risk_assessment(raw_analysis.get('risk_assessment', {})),
        'investigative_recommendations': raw_analysis.get('investigative_recommendations', []),

        # ── V2: AI Confidence Matrix ──
        'confidence_matrix': _build_confidence_matrix(raw_analysis.get('confidence_matrix', {})),

        # ── V2: AI Limitations ──
        'ai_limitations': raw_analysis.get('ai_limitations', []),

        # ── V2: Evidence Frame Index ──
        'evidence_frame_index': _build_evidence_frame_index(frames, raw_analysis),

        # ── V2: AI Processing Disclosure ──
        'ai_processing_disclosure': _build_ai_processing_disclosure(),

        # ── V2: Chain of Processing ──
        'chain_of_processing': _build_chain_of_processing(),

        # ── Evidence Exhibits ──
        'evidence_exhibits': _build_exhibits(frames, raw_analysis, frame_map),

        # ── Certification ──
        'certification': _build_certification(),

        # ── Legacy fields ──
        'environmental_conditions': raw_analysis.get('environmental_conditions', {}),
        'forensic_observations': raw_analysis.get('forensic_observations', ''),
        'confidence_score': raw_analysis.get('confidence_score', 0),
        'analysis_notes': raw_analysis.get('analysis_notes', ''),
        'engine_version': engine_version,
        'generated_at': datetime.now().isoformat(),
    }

    report['platform_verification'] = {
        'platform_name': PLATFORM_NAME,
        'platform_identifier': PLATFORM_IDENTIFIER,
        'platform_version': PLATFORM_VERSION,
        'generated_timestamp': report['generated_at'],
        'report_id': report['header']['report_id'],
    }
    report['report_integrity_hash'] = compute_report_integrity_hash(
        report,
        report['generated_at'],
        PLATFORM_IDENTIFIER,
    )

    return report


# ─────────────────────────────────────────────────────────
# SECTION BUILDERS
# ─────────────────────────────────────────────────────────

def _build_header(case_info):
    """Build report header with case information."""
    return {
        'report_title': 'EVIDENCE ANALYSIS REPORT',
        'system_name': 'Alfa Hawk — AI Evidence Analysis Platform | Alfa Labs, a child company of Alfa Groups',
        'classification': 'RESTRICTED — FOR OFFICIAL USE ONLY',
        'case_number': case_info.get('case_number') or "Not Provided",
        'report_id': f'RPT-{str(uuid.uuid4())[:8].upper()}',
        'date': datetime.now().strftime('%d %B %Y'),
        'time': datetime.now().strftime('%H:%M:%S IST'),
        'officer_id': case_info.get('officer_id') or "Not Provided",
        'case_description': case_info.get('case_description') or "Not Provided",
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
        scene = analysis['scene_description']
        content = scene if isinstance(scene, str) else scene.get('environment', 'N/A')
        sections.append({
            'title': 'Scene Overview',
            'content': content
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
            'observed_action': v.get('observed_action', v.get('description', 'No description')),
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


def _build_timeline(analysis, frame_map=None):
    """Build chronological timeline of events."""
    # Try both common keys for timeline events
    events = analysis.get('timeline_events', analysis.get('timeline', []))
    timeline = []
    for i, e in enumerate(events):
        raw_frame = e.get('evidence_frame', '')
        evidentiary_frame = frame_map.get(raw_frame, raw_frame) if frame_map else raw_frame
        
        timeline.append({
            'sequence': i + 1,
            'time': e.get('time_indicator', e.get('time', f'Event {i + 1}')),
            'event': e.get('event', e.get('description', 'No description')),
            'evidence_frame': evidentiary_frame,
        })
    return timeline


def _build_exhibits(frames, analysis, frame_map=None):
    """Build evidence exhibits gallery with analyzed frames."""
    exhibits = []

    # Get frame IDs that are linked to findings
    finding_frames = set()
    linked_sections = [
        'violations', 'accidents', 'number_plates', 'human_faces', 
        'timeline_events', 'timeline', 'persons', 'incident_phases', 'persons_identified'
    ]
    for section in linked_sections:
        for item in analysis.get(section, []):
            raw_fid = item.get('frame_id', item.get('evidence_frame', ''))
            fid = frame_map.get(raw_fid, raw_fid) if frame_map else raw_fid
            if fid and fid in frames:
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
        'system': 'Alfa Hawk — AI Evidence Analysis Platform',
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


# ─────────────────────────────────────────────────────────
# V2 SECTION BUILDERS
# ─────────────────────────────────────────────────────────

def _build_evidence_integrity(metadata):
    """Build evidence integrity section with SHA-256 hash and technical metadata."""
    integrity = {
        'sha256': metadata.get('evidence_sha256', 'Not computed'),
        'file_size_bytes': metadata.get('file_size_bytes', 0),
        'file_size_mb': metadata.get('file_size_mb', 0),
        'media_format': metadata.get('mime_type', 'Unknown'),
        'processing_timestamp': metadata.get('upload_timestamp', datetime.now().isoformat()),
    }

    # Video-specific integrity fields
    if metadata.get('width'):
        integrity['resolution'] = f"{metadata['width']} × {metadata['height']}"
    if metadata.get('fps'):
        integrity['frame_rate'] = f"{metadata['fps']} FPS"
    if metadata.get('duration_seconds'):
        mins = int(metadata['duration_seconds'] // 60)
        secs = int(metadata['duration_seconds'] % 60)
        integrity['duration'] = f"{mins}m {secs}s"
    if metadata.get('codec'):
        integrity['codec'] = metadata['codec']

    return integrity


def _build_incident_phases(phases, frame_map=None):
    """Build incident reconstruction phases table."""
    if not phases:
        return []

    enriched = []
    for i, phase in enumerate(phases):
        raw_frame = phase.get('evidence_frame', 'N/A')
        evidentiary_frame = frame_map.get(raw_frame, raw_frame) if frame_map else raw_frame
        
        enriched.append({
            'phase': phase.get('phase', i + 1),
            'description': phase.get('description', 'No description'),
            'time_range': phase.get('time_range', 'N/A'),
            'severity': phase.get('severity', 'low'),
            'evidence_frame': evidentiary_frame,
        })
    return enriched


def _build_scene_description(scene):
    """Handle object-based scene description."""
    if isinstance(scene, str):
        return {'environment': scene, 'camera_context': {}}
    return {
        'environment': scene.get('environment', 'No environmental description available.'),
        'camera_context': scene.get('camera_context', {})
    }


def _build_video_quality_assessment(quality):
    """Build video quality assessment section."""
    return {
        'resolution': quality.get('resolution', 'N/A'),
        'lighting': quality.get('lighting', 'N/A'),
        'motion_blur': quality.get('motion_blur', 'N/A'),
        'identification_reliability': quality.get('identification_reliability', 'N/A')
    }


def _build_person_registry(persons, frames, frame_map=None):
    """Build V2 person identification registry with P-ID system."""
    if not persons:
        return []

    enriched = []
    for i, p in enumerate(persons):
        raw_frame = p.get('first_seen', p.get('evidence_frame', p.get('frame_id', 'N/A')))
        evidentiary_frame = frame_map.get(raw_frame, raw_frame) if frame_map else raw_frame
        
        entry = {
            'index': i + 1,
            'person_id': p.get('person_id', f'P{i + 1}'),
            'description': p.get('description', 'No description'),
            'observed_role': p.get('observed_role', p.get('role', p.get('relevance', 'unknown'))).lower().replace('suspect', 'possible aggressor').replace('victim', 'possible victim'),
            'visibility_confidence': p.get('visibility_confidence', 'N/A'),
            'first_seen': p.get('first_seen', p.get('detected_at_timestamp', 'N/A')),
            'evidence_frame': evidentiary_frame,
            'actions': p.get('actions', []),
            'activity': p.get('activity', ''),
            'position': p.get('position_in_frame', ''),
        }
        # Link to evidence frame
        if evidentiary_frame and evidentiary_frame in frames:
            entry['evidence_frame_base64'] = frames[evidentiary_frame].get('base64', '')
        enriched.append(entry)
    return enriched


def _build_weapons_objects(objects):
    """Build weapons/objects detection table with confidence levels."""
    if not objects or len(objects) == 0:
        return [{
            'index': 1,
            'object': 'None Detected',
            'description': 'No object visually consistent with a weapon is clearly observable in the analyzed frames.',
            'timestamp': 'N/A',
            'confidence_level': 'N/A',
            'confidence_percent': 0,
            'frame_ref': 'N/A',
            'condition': 'N/A'
        }]

    enriched = []
    for i, obj in enumerate(objects):
        # Convert confidence level string to percentage
        conf_level = obj.get('confidence_level', obj.get('confidence', 'medium'))
        if isinstance(conf_level, str):
            conf_percent = CONFIDENCE_LEVEL_MAP.get(conf_level.lower(), 75)
        else:
            conf_percent = conf_level if isinstance(conf_level, (int, float)) else 75

        enriched.append({
            'index': i + 1,
            'object': obj.get('object', 'Unknown'),
            'description': obj.get('description', obj.get('relevance', '')),
            'timestamp': obj.get('timestamp', 'N/A'),
            'confidence_level': conf_level if isinstance(conf_level, str) else 'medium',
            'confidence_percent': conf_percent,
            'frame_ref': obj.get('frame_ref', ''),
            'condition': obj.get('condition', 'N/A'),
        })
    return enriched


def _build_evidence_frame_index(frames, analysis):
    """Build evidence frame index (F1, F2, F3…) referenced by other sections."""
    if not frames:
        return []

    index = []
    for i, (frame_id, frame_data) in enumerate(frames.items()):
        # Find what was detected in this frame
        findings = []
        
        # V2.1: Priority to short findings from Gemini
        timeline = analysis.get('timeline_events', [])
        for event in timeline:
            if event.get('evidence_frame') == f'F{i+1}' or event.get('evidence_frame') == frame_id:
                if event.get('short_finding'):
                    findings.append(event.get('short_finding'))
        
        # Fallback to automated mapping if findings still empty
        if not findings:
            for section_name in ['violations', 'accidents', 'number_plates', 'human_faces', 'persons']:
                for item in analysis.get(section_name, []):
                    if item.get('frame_id') == frame_id:
                        findings.append(item.get('description', item.get('type', 'Detection')))

        index.append({
            'frame_ref': f'F{i + 1}',
            'frame_id': frame_id,
            'timestamp': frame_data.get('timestamp_formatted', '00:00:00'),
            'description': frame_data.get('description', ''),
            'findings': findings,
        })
    return index


def _build_legal_classification(analysis):
    """Build legal classification using backend IPC mapping table.
    Gemini outputs events → our backend maps to IPC sections."""
    classifications = []
    seen = set()

    # Extract detected events from violations and incidents
    detected_events = analysis.get('detected_events', [])

    # Also scan violations for event types
    for violation in analysis.get('violations', []):
        event_type = violation.get('type', '').lower()
        event_desc = violation.get('description', '').lower()
        # Try to match against IPC mapping
        for event_key, ipc_info in IPC_MAPPING_TABLE.items():
            if event_key in event_type or event_key in event_desc:
                if ipc_info['section'] not in seen:
                    seen.add(ipc_info['section'])
                    classifications.append({
                        'activity': violation.get('description', event_key.title()),
                        'applicable_law': ipc_info['section'],
                        'law_description': ipc_info['description'],
                        'category': ipc_info['category'],
                    })

    # Also process explicit detected_events from Gemini
    for event in detected_events:
        event_name = event.get('event', '').lower()
        for event_key, ipc_info in IPC_MAPPING_TABLE.items():
            if event_key in event_name:
                if ipc_info['section'] not in seen:
                    seen.add(ipc_info['section'])
                    classifications.append({
                        'activity': event.get('event', event_key.title()),
                        'applicable_law': ipc_info['section'],
                        'law_description': ipc_info['description'],
                        'category': ipc_info['category'],
                    })

    # Also check incident phases for relevant events
    for phase in analysis.get('incident_phases', []):
        phase_desc = phase.get('description', '').lower()
        for event_key, ipc_info in IPC_MAPPING_TABLE.items():
            if event_key in phase_desc:
                if ipc_info['section'] not in seen:
                    seen.add(ipc_info['section'])
                    classifications.append({
                        'activity': phase.get('description', event_key.title()),
                        'applicable_law': ipc_info['section'],
                        'law_description': ipc_info['description'],
                        'category': ipc_info['category'],
                    })

    return {
        'classifications': classifications,
        'title': 'Indicative Legal Classifications',
        'disclaimer': 'Possible legal categories (indicative only). '
                      'All observations must be confirmed by qualified investigating officers '
                      'and legal counsel before any formal charges are filed.',
    }


def _build_confidence_matrix(matrix):
    """Build AI confidence matrix with labels (High/Medium/Low)."""
    if not matrix:
        return {}

    converted = {}
    for detection_type, value in matrix.items():
        label = 'Unknown'
        percent = 75
        
        if isinstance(value, str):
            label = value.capitalize()
            percent = CONFIDENCE_LEVEL_MAP.get(value.lower(), 75)
        elif isinstance(value, (int, float)):
            percent = int(value)
            if percent >= 85: label = 'High'
            elif percent >= 70: label = 'Medium'
            else: label = 'Low'
            
        converted[detection_type] = {
            'label': label,
            'percent': percent
        }
    return converted

def _build_risk_assessment(risk):
    """Build risk assessment with justification."""
    return {
        'threat_level': risk.get('threat_level', 'low').lower(),
        'risk_factors': risk.get('risk_factors', 'No obvious risk factors detected.'),
        'justification': risk.get('justification', 'Based on observable actions and presence of specific objects.'),
        'recommended_response': risk.get('recommended_response', 'Manual review recommended.')
    }


def _build_ai_processing_disclosure():
    """Build AI processing disclosure statement."""
    return (
        'Evidence media was analyzed using an external AI multimodal vision model '
        '(Google Gemini). Media was transmitted temporarily to the AI service for '
        'analysis and was deleted from the AI provider\'s servers immediately after '
        'processing. The AI service does not retain or store any evidence data. '
        'No evidence data is stored by this platform.'
    )


def _build_chain_of_processing():
    """Build chain of processing / evidence handling statement."""
    return {
        'statement': (
            'The uploaded media file was processed entirely in volatile memory. '
            'No copy of the evidence file, extracted frames, or analysis results '
            'are stored in persistent storage by this platform. All processing '
            'artifacts are destroyed after report generation and session expiry.'
        ),
        'processing_steps': [
            'Evidence file uploaded to in-memory buffer',
            'SHA-256 hash computed for integrity verification',
            'Media metadata extracted (resolution, codec, duration)',
            'Video uploaded to AI service for multimodal analysis',
            'AI analysis results received as structured JSON',
            'Structured forensic report compiled from analysis',
            'PDF report generated in-memory',
            'Evidence file deleted from AI service servers',
            'All in-memory artifacts scheduled for automatic cleanup',
        ],
    }



