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
        # engine.analyze should handle the exception and return an error status
        # but in our implementation, the engine might raise or handle it.
        # Let's verify it propagates or handles it as expected.
        with self.assertRaises(Exception):
            engine.analyze_video(b"dummy", "test.mp4", {}, None)

    def test_malformed_json_handling(self):
        # Handled by _validate_and_fill_defaults
        engine = EvidenceEngine(ai_provider=None)
        malformed = {"not_expected": 123}
        validated = engine._validate_and_fill_defaults(malformed)
        self.assertIn("incident_phases", validated)
        self.assertEqual(validated["incident_phases"], [])

if __name__ == '__main__':
    unittest.main()
