from abc import ABC, abstractmethod
import typing

class AIProvider(ABC):
    """
    Base interface for all AI Evidence Analysis providers.
    Ensures a standardized output schema for the evidence engine.
    """

    @abstractmethod
    def analyze_video(self, video_path: str, video_metadata: dict, api_key: str = None) -> dict:
        """
        Analyzes a video file and returns a structured analysis dictionary.
        
        Standardized Output Schema:
        {
            "executive_summary": str,
            "key_evidence_observations": [str],
            "scene_description": {
                "environment": str,
                "camera_context": {
                    "camera_position": str,
                    "field_of_view": str,
                    "visibility_limitations": str
                }
            },
            "video_quality_assessment": {
                "resolution": str,
                "lighting": str,
                "motion_blur": str,
                "identification_reliability": str
            },
            "incident_phases": [
                {
                    "phase": str,
                    "description": str,
                    "time_range": str,
                    "severity": str,
                    "evidence_frame": str
                }
            ],
            "persons": [
                {
                    "person_id": str,
                    "description": str,
                    "observed_role": str,
                    "visibility_confidence": str,
                    "first_seen": str,
                    "actions": [str]
                }
            ],
            "weapons_objects": [
                {
                    "object": str,
                    "description": str,
                    "timestamp": str,
                    "confidence_level": str,
                    "confidence_percent": int,
                    "held_by": str,
                    "frame_ref": str
                }
            ],
            "timeline": [
                {
                    "time": str,
                    "event": str,
                    "short_finding": str,
                    "evidence_frame": str
                }
            ],
            "legal_classification": {
                "disclaimer": str,
                "classifications": [
                    {
                        "activity": str,
                        "applicable_law": str,
                        "law_description": str,
                        "category": str
                    }
                ]
            },
            "risk_assessment": {
                "threat_level": str,
                "risk_factors": str,
                "justification": str,
                "recommended_response": str
            },
            "confidence_matrix": {
                "object_recognition": {"percent": int, "label": str},
                "scene_understanding": {"percent": int, "label": str},
                "event_reconstruction": {"percent": int, "label": str},
                "identity_consistency": {"percent": int, "label": str}
            },
            "limitations": [str]
        }
        """
        pass
