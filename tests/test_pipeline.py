import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

from coupang_api import CoupangPartnersClient
from content_generator import generate_dashboard_post, DISCLOSURE_TEXT

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_demo_without_credentials_or_network(self):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('COUPANG_', 'GEMINI_', 'KAKAO_'))}
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--demo'],
                                    cwd=folder, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            draft = json.loads((Path(folder) / 'artifacts/draft.json').read_text())
            self.assertTrue(draft['demo'])
            self.assertIn(DISCLOSURE_TEXT, draft['body'])

    def test_business_error_is_not_empty_search(self):
        response = Mock()
        response.json.return_value = {'rCode': 'ERROR', 'data': {}}
        client = CoupangPartnersClient('test-access', 'test-secret')
        with patch('coupang_api.requests.request', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'ERROR'):
                client.search_products('수납')

    def test_disclosure_does_not_depend_on_model_output(self):
        with patch('content_generator._dashboard_model.generate_content',
                   return_value=Mock(text='모델이 생성한 소개')):
            result = generate_dashboard_post('수납함', '')
        self.assertTrue(result.startswith(DISCLOSURE_TEXT))


if __name__ == '__main__':
    unittest.main()
