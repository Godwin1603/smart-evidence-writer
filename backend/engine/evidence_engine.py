import logging
import hashlib
import os
import tempfile
import cv2
from datetime import datetime
from .media_processor import get_media_metadata
from .frame_extractor import extract_key_frames, image_to_frame_entry
from backend.reporting.report_builder import build_forensic_report
from backend.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)

class EvidenceEngine:
    """
    Open Source Core: The primary orchestrator for evidence analysis.
    Decouples the analysis pipeline from the server/platform logic.
    """
    
    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider
        self.version = "1.1.0"
        self.schema_version = "1.0"

    def _pre_check_analysis(self, file_bytes: bytes, filename: str):
        """Perform sanity checks before calling AI provider."""

        # 1. Zero Duration / Empty File
        if not file_bytes:
            raise ValueError("Empty evidence file provided.")

        # 2. Frame Count & Sanity
        ext = os.path.splitext(filename)[1].lower()
        if ext in {'.mp4', '.mov', '.avi'}:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                cap = cv2.VideoCapture(tmp_path)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                duration = frame_count / fps if fps > 0 else 0
                
                if frame_count < 5:
                    raise ValueError(f"Evidence file contains too few frames ({frame_count}) for reliable AI analysis.")
                if duration <= 0:
                    raise ValueError("Evidence file has zero or invalid duration.")
                cap.release()
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def _validate_and_fill_defaults(self, raw_analysis: dict) -> dict:
        """Ensure LLM response matches schema; fill defaults if malformed."""
        defaults = {
            "schema_version": self.schema_version,
            "incident_phases": [],
            "persons": [],
            "objects": [],
            "timeline": [],
            "confidence_matrix": {},
            "limitations": [],
            "key_evidence_observations": [],
            "video_quality_assessment": {}
        }
        
        if not isinstance(raw_analysis, dict):
            logger.warning("AI Provider returned non-dict response. Using defaults.")
            return defaults

        for key, default_val in defaults.items():
            if key not in raw_analysis:
                raw_analysis[key] = default_val
        
        return raw_analysis

    def run_analysis(self, file_bytes: bytes, filename: str, case_data: dict, 
                     api_key: str = None, progress_callback: callable = None) -> dict:
        """
        Executes the full forensic analysis pipeline.
        """
        def update_prog(p, m):
            if progress_callback: progress_callback(p, m)
            logger.info(f"Engine: {p}% - {m}")

        # 0. Pre-check
        update_prog(2, "Performing evidence sanity pre-checks...")
        self._pre_check_analysis(file_bytes, filename)

        update_prog(5, "Calculating evidence integrity hash...")
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        update_prog(10, "Extracting media metadata...")
        metadata = get_media_metadata(file_bytes, filename)
        metadata['sha256'] = file_hash
        
        # 1. Extract Frames
        update_prog(20, "Extracting evidence frames for analysis...")
        ext = os.path.splitext(filename)[1].lower()
        if ext in {'.MP4', '.MOV', '.AVI', '.mp4', '.mov', '.avi'}:
            frames = extract_key_frames(file_bytes, original_filename=filename)
        else:
            frames = image_to_frame_entry(file_bytes, filename=filename)
        update_prog(35, f"Extracted {len(frames)} frames successfully.")

        # 2. AI Analysis
        update_prog(40, "Handing off to AI Provider for forensic reconstruction...")
        
        ext = os.path.splitext(filename)[1] or '.mp4'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            raw_analysis = self.ai_provider.analyze_video(tmp_path, metadata, api_key=api_key)
            
            update_prog(75, "Validating AI response schema...")
            validated_analysis = self._validate_and_fill_defaults(raw_analysis)
            
            update_prog(80, "AI analysis complete. Applying forensic structuring...")
            
            # 3. Build Report
            report = build_forensic_report(
                raw_analysis=validated_analysis,
                metadata=metadata,
                frames=frames,
                case_data=case_data,
                engine_version=self.version
            )
            
            update_prog(100, "Forensic report finalized.")
            return report

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
