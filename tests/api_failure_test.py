import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add root and backend to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'backend'))

from backend.engine.evidence_engine import EvidenceEngine

class TestAPIFailure(unittest.TestCase):
    def test_provider_timeout(self):
        mock_provider = MagicMock()
        mock_provider.analyze_video.side_effect = Exception("Deadline Exceeded")
        
        engine = EvidenceEngine(ai_provider=mock_provider)
        with patch("backend.engine.evidence_engine.get_media_metadata", return_value={"filename": "test.mp4"}), \
             patch("backend.engine.evidence_engine.extract_key_frames", return_value={}), \
             patch("backend.engine.evidence_engine.build_forensic_report", return_value={"header": {"report_id": "RPT-TEST"}}), \
             patch.object(engine, "_pre_check_analysis", return_value=None):
            with self.assertRaises(Exception):
                engine.run_analysis(
                    file_bytes=b"dummy-bytes",
                    filename="test.mp4",
                    case_data={},
                    api_key=None,
                    progress_callback=None,
                )

    def test_malformed_json_handling(self):
        # Handled by _validate_and_fill_defaults
        engine = EvidenceEngine(ai_provider=None)
        malformed = {"not_expected": 123}
        validated = engine._validate_and_fill_defaults(malformed)
        self.assertIn("incident_phases", validated)
        self.assertEqual(validated["incident_phases"], [])

if __name__ == '__main__':
    unittest.main()
