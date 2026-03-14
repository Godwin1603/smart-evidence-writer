import os
import json
import logging
import time
import tempfile
from google import genai
from google.genai import types
from .base import AIProvider

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    """
    Google Gemini implementation of the AIProvider interface.
    """

    SYSTEM_INSTRUCTION = """You are a senior multimodal forensic evidence analyst assisting Indian law enforcement.
Your job is to OBSERVE and DESCRIBE what is visible in video evidence, then produce a structured JSON forensic report.

CRITICAL LANGUAGE RULES — FOLLOW THESE EXACTLY:
- You are an OBSERVER, not a judge. Describe ONLY what is visually observable.
- NEVER declare legal conclusions or interpret intent (no "murder", "fatal", "attacker", "provoked").
- Use neutral hedging language: "appears to perform a movement", "consistent with", "visible in the vicinity".
- Instead of "P2 attacks P1", say "P2 appears to perform an arm movement toward P1".
- NEVER confirm fatalities or motive. Say "subject remains motionless on the ground" instead of "fatality".
- For roles: use "participant", "possible aggressor", "possible victim", "subject", "bystander".
- Every claim MUST reference a frame reference (e.g., F1, F2).
- Ensure all observations are linked to specific moments and frames.

Output ONLY raw parseable JSON. No markdown. No explanation. No commentary."""

    V2_FORENSIC_PROMPT = """Watch this video evidence VERY carefully. Your analysis will be used in a legal investigation.

LANGUAGE SAFETY RULES (MANDATORY — violating these makes the report inadmissible):
1. You are an OBSERVER. Describe ONLY what is VISIBLE. Never declare legal conclusions (murder, fatal, assault).
2. Avoid interpreting intent. Instead of "P2 attacks P1", use "P2 appears to make physical contact with P1".
3. Use hedging language: "appears to", "what appears to be", "consistent with", "visually observable".
4. NEVER confirm: fatalities, guilt, motive, or leadership roles.
5. INSTEAD use: "individual collapses", "remains motionless", "possible aggressor", "subject".
6. Executive summary must be strictly observational.
   BAD: "P2 fatally attacks P1."
   GOOD: "P2 appears to perform a downward arm movement toward P1 while P1 remains on the ground."

EVIDENCE LINKING RULES (MANDATORY):
7. EVERY claim must reference a frame (Frame F1/F2/etc).
8. Timeline events must end with a frame reference like "(Frame F3)".
9. Each phase in incident reconstruction must link to its primary supporting frame.

Return ONLY valid JSON in this exact format:
{
    "executive_summary": "Strictly OBSERVATIONAL 2-3 sentence overview.",
    "key_evidence_observations": ["Bullet point 1", "Bullet point 2"],
    "scene_description": {
        "environment": "Location details",
        "camera_context": {
            "camera_position": "Surveillance/Handheld",
            "field_of_view": "Description",
            "visibility_limitations": "Lighting/Obstructions"
        }
    },
    "video_quality_assessment": {
        "resolution": "Low/Medium/High",
        "lighting": "Clear/Poor",
        "motion_blur": "Minimal/High",
        "identification_reliability": "High/Low"
    },
    "incident_phases": [
        {
            "phase": 1,
            "description": "...",
            "time_range": "00:00:00-00:00:05",
            "severity": "low/medium/high/critical",
            "evidence_frame": "F1"
        }
    ],
    "persons": [
        {
            "person_id": "P1",
            "description": "...",
            "observed_role": "...",
            "visibility_confidence": "High/Medium/Low",
            "first_seen": "00:00:01",
            "actions": ["..."]
        }
    ],
    "weapons_objects": [
        {
            "object": "...",
            "description": "...",
            "timestamp": "00:00:08",
            "confidence_level": "low/medium/high",
            "held_by": "P1 or N/A",
            "frame_ref": "F1"
        }
    ],
    "timeline": [
        {
            "time": "00:00:05",
            "event": "Description (Frame F1)",
            "evidence_frame": "F1",
            "short_finding": "Summary"
        }
    ],
    "legal_classification": {
        "disclaimer": "...",
        "classifications": [
            {
                "activity": "...",
                "applicable_law": "...",
                "law_description": "...",
                "category": "..."
            }
        ]
    },
    "risk_assessment": {
        "threat_level": "...",
        "risk_factors": "...",
        "justification": "...",
        "recommended_response": "..."
    },
    "confidence_matrix": {
        "object_recognition": {"percent": 85, "label": "High"},
        "scene_understanding": {"percent": 90, "label": "High"},
        "event_reconstruction": {"percent": 80, "label": "Medium"},
        "identity_consistency": {"percent": 75, "label": "Medium"}
    },
    "limitations": ["lighting", "blur"]
}"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment.")
        self.client = genai.Client(api_key=self.api_key)
        self.max_retries = 2

    def verify_api_key(self, api_key: str) -> bool:
        """Verify the API key is valid by making a lightweight request."""
        try:
            test_client = genai.Client(api_key=api_key)
            # Just attempt to list models – a common way to check key validity
            # We only need to check if it doesnt raise an unauthorized error
            test_client.models.list(config={'page_size': 1})
            return True
        except Exception as e:
            logger.warning("Gemini Key Verification Failed.")
            # Do NOT log the actual exception as it might contain key details or sensitive info
            return False

    def _upload_and_wait(self, tmp_path, mime_type="video/mp4"):
        logger.info("Gemini: Uploading video...")
        video_file = self.client.files.upload(file=tmp_path, config={'mime_type': mime_type})
        
        while video_file.state.name == 'PROCESSING':
            time.sleep(5)
            video_file = self.client.files.get(name=video_file.name)
            
        if video_file.state.name == 'FAILED':
            raise Exception("Gemini processing failed.")
        return video_file

    def analyze_video(self, video_path: str, video_metadata: dict = None, api_key: str = None) -> dict:
        # Override key if provided
        if api_key:
            self.client = genai.Client(api_key=api_key)

        video_file = None
        try:
            video_file = self._upload_and_wait(video_path)
            
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[video_file, self.V2_FORENSIC_PROMPT],
                        config=types.GenerateContentConfig(
                            system_instruction=self.SYSTEM_INSTRUCTION,
                            temperature=0.1,
                            response_mime_type="application/json",
                        )
                    )
                    
                    result_text = response.text.strip()
                    # Clean markdown
                    if result_text.startswith('```json'): result_text = result_text[7:]
                    elif result_text.startswith('```'): result_text = result_text[3:]
                    if result_text.endswith('```'): result_text = result_text[:-3]
                    
                    return json.loads(result_text.strip())
                except Exception as e:
                    last_error = e
                    logger.warning(f"Gemini attempt {attempt+1} failed: {e}")
                    time.sleep(2)
            
            raise Exception(f"Gemini analysis failed after retries: {last_error}")

        finally:
            if video_file:
                try:
                    self.client.files.delete(name=video_file.name)
                except:
                    pass
