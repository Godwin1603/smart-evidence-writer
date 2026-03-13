# utils/ai_analyzer.py — AI analysis using Groq with Local OCR integration
import os
import sys
import json
import base64
import logging
from datetime import datetime

# Path correction
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(UTILS_DIR)
sys.path.append(BACKEND_DIR)

from config import GROQ_API_KEY, GROQ_VISION_MODEL, GROQ_TEXT_MODEL
from utils.ocr_processor import extract_text_from_image, get_ocr_hint_for_prompt

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# INITIALIZE GROQ CLIENT
# ─────────────────────────────────────────────────────────

groq_client = None
try:
    from groq import Groq
    if GROQ_API_KEY and GROQ_API_KEY != 'your_groq_api_key_here':
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Groq AI client initialized")
    else:
        logger.warning("⚠️ Groq API key not set")
except ImportError:
    logger.warning("⚠️ Groq library not installed")


# ─────────────────────────────────────────────────────────
# EVIDENCE ANALYSIS PROMPTS
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a senior forensic evidence analyst at a law enforcement crime lab. "
    "Your analysis is used as legal evidence in court. Be extremely thorough. "
    "Your TOP PRIORITY is reading vehicle registration/number plates — "
    "read every character, even partial ones. A missed plate could let a suspect escape. "
    "Always return valid, parseable JSON and nothing else."
)

EVIDENCE_ANALYSIS_PROMPT = """You are an expert forensic evidence analyst working for a law enforcement agency.
Analyze this evidence thoroughly and return a STRUCTURED JSON response.

CRITICAL PRIORITIES — you MUST follow these in order of importance:
1. NUMBER PLATES: This is your TOP PRIORITY. Examine EVERY vehicle. If there is ANY vehicle, look carefully at the front AND rear for registration plates. Read every character you can see — even partial plates are valuable. Do NOT skip this. Even if the plate is blurry, angled, partially occluded, or far away, attempt to read it and report what you CAN see. Use "?" for unreadable characters (e.g., "TN 37 C? 1234"). If a plate is physically visible but unreadable, still report the vehicle and note "plate visible but unreadable".
2. HUMAN FACES & PERSONS: Describe every visible person — clothing, age estimate, activity, position.
3. VIOLATIONS & ACCIDENTS: Document any traffic violations, accidents, property damage, or criminal activity.
4. SCENE DETAILS: Environment, landmarks, road signs, lighting, weather.

You MUST identify and report on ALL of the following categories. For each category, provide detailed findings or explicitly state "None detected".

Return ONLY valid JSON in this exact format (no markdown, no code fences):
{
    "executive_summary": "A 2-3 sentence overview of what this evidence shows",
    "scene_description": "Detailed description of the scene, environment, lighting, weather conditions visible",
    "violations": [
        {
            "type": "traffic/criminal/safety/regulatory",
            "description": "Detailed description of the violation",
            "severity": "critical/high/medium/low",
            "evidence_details": "What in the image supports this finding"
        }
    ],
    "accidents": [
        {
            "type": "vehicle collision/pedestrian/property damage/other",
            "description": "Detailed description of the accident",
            "severity": "fatal/severe/moderate/minor",
            "vehicles_involved": "Description of vehicles involved",
            "damage_assessment": "Description of visible damage"
        }
    ],
    "number_plates": [
        {
            "plate_text": "EXACT text on the plate — read every character, use ? for unreadable ones. NEVER put None here if a plate is visible.",
            "vehicle_type": "car/truck/motorcycle/bus/auto-rickshaw/van/suv/etc",
            "vehicle_color": "Color of the vehicle",
            "vehicle_make_model": "Make/model if identifiable (e.g., Hyundai i20, Honda Activa)",
            "plate_region": "State/region based on plate format (e.g., TN=Tamil Nadu, KA=Karnataka, MH=Maharashtra)",
            "plate_position": "front/rear/side — where is the plate visible from",
            "readability": "clear/partial/blurry/occluded",
            "confidence": "high/medium/low"
        }
    ],
    "human_faces": [
        {
            "person_id": "Person 1, Person 2, etc.",
            "description": "Age estimate, gender, distinguishing features, clothing",
            "position_in_frame": "Where in the image this person appears",
            "activity": "What the person appears to be doing",
            "relevance": "Witness/suspect/victim/bystander"
        }
    ],
    "landmarks": [
        {
            "name": "Name or description of the landmark",
            "type": "building/sign/monument/road/intersection/etc",
            "details": "Additional details about the landmark",
            "location_hint": "Any clues about geographic location"
        }
    ],
    "objects_of_interest": [
        {
            "object": "Name of the object",
            "description": "Why it is relevant to the investigation",
            "condition": "Condition or state of the object"
        }
    ],
    "timeline_events": [
        {
            "time_indicator": "Any timestamp or time reference visible",
            "event": "Description of what is happening"
        }
    ],
    "environmental_conditions": {
        "lighting": "Day/Night/Artificial/Mixed",
        "weather": "Clear/Rainy/Foggy/etc if visible",
        "visibility": "Good/Poor/Moderate"
    },
    "forensic_observations": "Any anomalies, signs of tampering, or forensic notes",
    "risk_assessment": {
        "threat_level": "critical/high/medium/low/none",
        "risk_factors": "Specific risk factors identified",
        "recommended_response": "Suggested immediate actions"
    },
    "investigative_recommendations": [
        "Specific follow-up action 1",
        "Specific follow-up action 2"
    ],
    "confidence_score": 0.85,
    "analysis_notes": "Any additional observations or caveats about this analysis"
}

REMINDER: If you see ANY vehicle, you MUST check for its number plate. A missing plate in your response when one is visible is an UNACCEPTABLE error."""


AUDIO_ANALYSIS_PROMPT = """You are an expert forensic evidence analyst working for a law enforcement agency.
Analyze this audio transcript from evidence and return a STRUCTURED JSON response.

The following is a transcript of an audio evidence file:
---
{transcript}
---

Return ONLY valid JSON in this exact format (no markdown, no code fences):
{
    "executive_summary": "A 2-3 sentence overview of what this audio evidence reveals",
    "transcript_summary": "Condensed summary of the conversation/audio content",
    "speakers_identified": [
        {
            "speaker_id": "Speaker 1, Speaker 2, etc.",
            "description": "Voice characteristics, language, accent if notable",
            "role": "Estimated role: caller/responder/witness/suspect/officer"
        }
    ],
    "violations": [
        {
            "type": "Type of violation mentioned or implied",
            "description": "Details from the transcript",
            "severity": "critical/high/medium/low"
        }
    ],
    "key_mentions": {
        "names": ["Any names mentioned"],
        "locations": ["Any locations mentioned"],
        "phone_numbers": ["Any phone numbers mentioned"],
        "dates_times": ["Any dates or times mentioned"],
        "vehicle_references": ["Any vehicle descriptions or plate numbers mentioned"]
    },
    "emotional_tone": "Overall emotional tone of the audio (calm/agitated/threatening/etc)",
    "timeline_events": [
        {
            "time_indicator": "Approximate position in audio or mentioned time",
            "event": "What is being discussed"
        }
    ],
    "risk_assessment": {
        "threat_level": "critical/high/medium/low/none",
        "risk_factors": "Specific risk factors identified from conversation",
        "recommended_response": "Suggested actions"
    },
    "investigative_recommendations": [
        "Follow-up action 1",
        "Follow-up action 2"
    ],
    "confidence_score": 0.75,
    "analysis_notes": "Additional observations about the audio evidence"
}"""


# ─────────────────────────────────────────────────────────
# CORE ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────────────────

def analyze_image(image_bytes_or_base64, metadata=None):
    """Analyze a single image using Groq with Local OCR assistance."""
    if groq_client is None:
        return _fallback_analysis('image', metadata, 'Groq client not initialized')

    try:
        # 1. Run Local OCR first to get hints
        image_bytes = image_bytes_or_base64
        if isinstance(image_bytes_or_base64, str):
            image_bytes = base64.b64decode(image_bytes_or_base64)
            b64_str = image_bytes_or_base64
        else:
            b64_str = base64.b64encode(image_bytes).decode('utf-8')
            
        logger.info("Running local OCR for hints...")
        ocr_results = extract_text_from_image(image_bytes)
        ocr_hint = get_ocr_hint_for_prompt(ocr_results)
        
        if ocr_hint:
            logger.info(f"Local OCR hints generated: {ocr_hint.strip()}")

        context = ""
        if metadata:
            meta_copy = {k: v for k, v in metadata.items() if k != 'file_bytes'}
            context = f"\n\nFile metadata: {json.dumps(meta_copy, default=str)}"

        # 2. Combine Prompt + OCR Hint
        full_prompt = EVIDENCE_ANALYSIS_PROMPT + context + "\n\n" + ocr_hint

        # 3. Call Groq
        response = groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": full_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_str}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=6000,
            top_p=0.8,
        )

        result_text = response.choices[0].message.content.strip()
        return _parse_ai_response(result_text)
    except Exception as e:
        logger.error(f"Groq image analysis failed: {e}")
        return _fallback_analysis('image', metadata, str(e))


def analyze_video_frames(frames_dict, metadata=None):
    """Analyze extracted video frames using Groq + Local OCR."""
    all_analyses = []
    frame_analyses = {}

    for frame_id, frame_data in frames_dict.items():
        try:
            # frame_data['base64'] is already available
            analysis = analyze_image(frame_data['base64'], metadata)
            analysis['frame_id'] = frame_id
            analysis['timestamp'] = frame_data.get('timestamp', 0)
            analysis['timestamp_formatted'] = frame_data.get('timestamp_formatted', '00:00:00')
            all_analyses.append(analysis)
            frame_analyses[frame_id] = analysis
        except Exception as e:
            logger.warning(f"Frame {frame_id} analysis failed: {e}")

    combined = _combine_frame_analyses(all_analyses, metadata)
    combined['frame_analyses'] = frame_analyses
    return combined


def analyze_audio(transcript, metadata=None):
    """Analyze audio transcript using Groq."""
    if groq_client is None:
        return _fallback_analysis('audio', metadata, 'Groq client not initialized')

    if not transcript or transcript.startswith('['):
        return _fallback_analysis('audio', metadata, "No transcript available")

    try:
        prompt = AUDIO_ANALYSIS_PROMPT.format(transcript=transcript)
        response = groq_client.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4096,
            top_p=0.8,
        )

        result_text = response.choices[0].message.content.strip()
        parsed = _parse_ai_response(result_text)
        parsed['transcript'] = transcript
        return parsed
    except Exception as e:
        logger.error(f"Groq audio analysis failed: {e}")
        return _fallback_analysis('audio', metadata, str(e))


# Placeholder for direct video analysis (not used in this stack)
def analyze_video(video_bytes, metadata=None):
    return None

def is_gemini_available():
    return False


# ─────────────────────────────────────────────────────────
# HELPER FUNCTIONS (Preserved from original)
# ─────────────────────────────────────────────────────────

def _parse_ai_response(response_text):
    """Parse the JSON response from AI, handling common formatting issues."""
    text = response_text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed, attempting repair: {e}")

        # Try to find JSON object in the response
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Return as raw text analysis
        return {
            'executive_summary': text[:500],
            'raw_analysis': text,
            'parse_error': True,
            'violations': [],
            'accidents': [],
            'number_plates': [],
            'human_faces': [],
            'landmarks': [],
            'objects_of_interest': [],
            'confidence_score': 0.5,
            'analysis_notes': 'AI response could not be parsed as structured JSON'
        }


def _combine_frame_analyses(analyses, metadata=None):
    """Combine multiple frame analyses into a single comprehensive report."""
    if not analyses:
        return _fallback_analysis('video', metadata, "No frames analyzed")

    combined = {
        'executive_summary': '',
        'scene_description': '',
        'violations': [],
        'accidents': [],
        'number_plates': [],
        'human_faces': [],
        'landmarks': [],
        'objects_of_interest': [],
        'timeline_events': [],
        'environmental_conditions': {},
        'forensic_observations': '',
        'risk_assessment': {},
        'investigative_recommendations': [],
        'confidence_score': 0,
        'analysis_notes': '',
    }

    seen_plates = set()
    seen_violations = set()
    summaries = []

    for analysis in analyses:
        ts = analysis.get('timestamp_formatted', '?')

        if analysis.get('executive_summary'):
            summaries.append(f"[{ts}] {analysis['executive_summary']}")

        for v in analysis.get('violations', []):
            key = v.get('description', '')[:50]
            if key and key not in seen_violations:
                seen_violations.add(key)
                v['detected_at_timestamp'] = ts
                v['frame_id'] = analysis.get('frame_id')
                combined['violations'].append(v)

        for a in analysis.get('accidents', []):
            a['detected_at_timestamp'] = ts
            a['frame_id'] = analysis.get('frame_id')
            combined['accidents'].append(a)

        for p in analysis.get('number_plates', []):
            plate_text = p.get('plate_text', '').upper().strip()
            if plate_text and plate_text not in seen_plates and plate_text != 'NONE':
                seen_plates.add(plate_text)
                p['detected_at_timestamp'] = ts
                p['frame_id'] = analysis.get('frame_id')
                combined['number_plates'].append(p)

        for f in analysis.get('human_faces', []):
            f['detected_at_timestamp'] = ts
            f['frame_id'] = analysis.get('frame_id')
            combined['human_faces'].append(f)

        for l in analysis.get('landmarks', []):
            l['detected_at_timestamp'] = ts
            combined['landmarks'].append(l)

        for o in analysis.get('objects_of_interest', []):
            combined['objects_of_interest'].append(o)

        combined['timeline_events'].append({
            'time_indicator': ts,
            'event': analysis.get('executive_summary', 'Frame analyzed')
        })

        if analysis.get('environmental_conditions'):
            combined['environmental_conditions'] = analysis['environmental_conditions']

        if analysis.get('risk_assessment', {}).get('threat_level'):
            current = combined['risk_assessment'].get('threat_level', 'none')
            new_level = analysis['risk_assessment']['threat_level']
            threat_order = {'none': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            if threat_order.get(new_level, 0) > threat_order.get(current, 0):
                combined['risk_assessment'] = analysis['risk_assessment']

        for rec in analysis.get('investigative_recommendations', []):
            if rec not in combined['investigative_recommendations']:
                combined['investigative_recommendations'].append(rec)

        combined['confidence_score'] += analysis.get('confidence_score', 0)

    if analyses:
        combined['confidence_score'] = round(combined['confidence_score'] / len(analyses), 2)

    combined['executive_summary'] = f"Video analysis of {len(analyses)} frames with Local OCR assistance. " + " ".join(summaries[:3])
    combined['scene_description'] = analyses[0].get('scene_description', '') if analyses else ''
    combined['forensic_observations'] = '; '.join(
        a.get('forensic_observations', '') for a in analyses if a.get('forensic_observations')
    )

    return combined


def _fallback_analysis(media_type, metadata=None, error=None):
    """Generate a fallback analysis when AI is unavailable."""
    return {
        'executive_summary': f'Evidence file ({media_type}) received for analysis. AI analysis unavailable — manual review required.',
        'scene_description': 'Unable to analyze — AI service not configured or unavailable.',
        'violations': [],
        'accidents': [],
        'number_plates': [],
        'human_faces': [],
        'landmarks': [],
        'objects_of_interest': [],
        'timeline_events': [],
        'environmental_conditions': {},
        'forensic_observations': f'Automated analysis unavailable. Error: {error}' if error else 'Automated analysis unavailable.',
        'risk_assessment': {
            'threat_level': 'unknown',
            'risk_factors': 'Cannot assess — manual review needed',
            'recommended_response': 'Assign to investigating officer for manual review'
        },
        'investigative_recommendations': [
            'Manual review of evidence file required',
            'Configure AI API key for automated analysis'
        ],
        'confidence_score': 0.0,
        'analysis_notes': 'Fallback report — AI analysis was not available',
        'metadata': metadata or {},
        'is_fallback': True,
    }