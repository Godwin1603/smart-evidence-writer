import json
import unittest
import os
import sys

# Add root and backend to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'backend'))

from backend.engine.evidence_engine import EvidenceEngine

class MockAIProvider:
    def __init__(self, mock_response):
        self.mock_response = mock_response
    
    def analyze_video(self, video_bytes, filename, case_data, progress_callback):
        return self.mock_response

class TestSchemaValidation(unittest.TestCase):
    def setUp(self):
        self.valid_schema = {
            "schema_version": "1.0",
            "incident_phases": [{"phase": 1, "description": "test"}],
            "persons": [{"person_id": "P1", "description": "test"}],
            "objects": [],
            "timeline": [],
            "confidence_matrix": {},
            "limitations": []
        }

    def test_complete_schema(self):
        engine = EvidenceEngine(ai_provider=None)
        # Manually verify internal validation logic
        validated = engine._validate_and_fill_defaults(self.valid_schema)
        self.assertEqual(validated["schema_version"], "1.0")
        self.assertEqual(len(validated["incident_phases"]), 1)

    def test_missing_fields_filling(self):
        malformed = {
            "incident_phases": [{"phase": 1, "description": "test"}]
            # missing everything else
        }
        engine = EvidenceEngine(ai_provider=None)
        validated = engine._validate_and_fill_defaults(malformed)
        
        self.assertIn("persons", validated)
        self.assertEqual(validated["persons"], [])
        self.assertIn("schema_version", validated)
        self.assertEqual(validated["schema_version"], "1.0")

    def test_non_dict_response(self):
        malformed = "not a dict"
        engine = EvidenceEngine(ai_provider=None)
        validated = engine._validate_and_fill_defaults(malformed)
        
        self.assertIsInstance(validated, dict)
        self.assertIn("incident_phases", validated)
        self.assertEqual(validated["incident_phases"], [])

if __name__ == '__main__':
    unittest.main()
