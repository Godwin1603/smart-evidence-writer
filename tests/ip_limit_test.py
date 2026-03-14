import unittest
import sys
import os
import time

# Add root and backend to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'backend'))

from unittest.mock import MagicMock
from flask import Flask, request, jsonify
from backend.app import app, check_limits, PLATFORM_LIMITS, usage_stats, ip_usage, global_stats

class TestIPLimits(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.client_id = "TEST-CLIENT-123"
        # Reset stats for testing
        usage_stats.clear()
        ip_usage.clear()
        global_stats['total_daily_count'] = 0

    def test_client_id_missing(self):
        response = self.app.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"X-Client-ID header missing", response.data)

    def test_cooldown_active(self):
        # First request
        headers = {'X-Client-ID': self.client_id}
        # Simulate app/upload logic that updates last_request_at
        usage_stats[self.client_id]['last_request_at'] = time.time()
        
        # Second request immediate
        response = self.app.post('/api/upload', headers=headers)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Request cooldown active", response.data)

    def test_global_limit(self):
        global_stats['total_daily_count'] = PLATFORM_LIMITS['global_daily']
        headers = {'X-Client-ID': self.client_id}
        response = self.app.post('/api/upload', headers=headers)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Platform daily capacity reached", response.data)

if __name__ == '__main__':
    unittest.main()
