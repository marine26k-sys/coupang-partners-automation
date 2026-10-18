import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from dotenv import dotenv_values
import json
from mailer import _get_access_token, send_draft_kakao
from run_scheduled import redact


class LocalRuntimeTests(unittest.TestCase):
    def test_long_drafts_are_sent_without_truncation(self):
        response = Mock()
        response.json.return_value = {'result_code': 0}
        daily = '가' * 1500
        hook = '나' * 1200
        with patch('mailer._get_access_token', return_value='test-access'), \
             patch('mailer.requests.post', return_value=response) as send:
            send_draft_kakao(daily, hook, '상품', 'https://example.com/item')
        parts = [json.loads(call.kwargs['data']['template_object'])['text']
                 for call in send.call_args_list]
        self.assertTrue(all(len(part) <= 1000 for part in parts))
        self.assertIn(daily, ''.join(parts))
        self.assertIn(hook, ''.join(parts))

    def test_refresh_rotation_is_saved_privately(self):
        with tempfile.TemporaryDirectory() as folder:
            env_file = Path(folder) / '.env'
            env_file.write_text('KAKAO_REFRESH_TOKEN=old-token\n')
            response = Mock()
            response.json.return_value = {'access_token': 'access', 'refresh_token': 'new-token'}
            with patch.dict(os.environ, {'KAKAO_REST_API_KEY': 'test-key',
                                         'KAKAO_REFRESH_TOKEN': 'old-token'}, clear=True), \
                 patch('mailer.__file__', str(Path(folder) / 'mailer.py')), \
                 patch('mailer.requests.post', return_value=response):
                self.assertEqual(_get_access_token(), 'access')
                self.assertEqual(os.environ['KAKAO_REFRESH_TOKEN'], 'new-token')
            self.assertEqual(dotenv_values(env_file)['KAKAO_REFRESH_TOKEN'], 'new-token')
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)

    def test_log_redacts_credentials_and_oauth_query_values(self):
        text = 'secret-value code=authorization&state=nonce refresh_token=rotated'
        result = redact(text, {'GEMINI_API_KEY': 'secret-value'})
        for value in ('secret-value', 'authorization', 'nonce', 'rotated'):
            self.assertNotIn(value, result)


if __name__ == '__main__':
    unittest.main()


class ThreeDailySlotsTests(unittest.TestCase):
    def test_three_daily_runs_have_distinct_duplicate_keys(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from run_scheduled import scheduled_run_key
        zone=ZoneInfo('Asia/Seoul')
        self.assertEqual([scheduled_run_key(datetime(2026,10,18,h,tzinfo=zone)) for h in (9,13,18)],
                         ['2026-10-18-09','2026-10-18-13','2026-10-18-18'])
        self.assertEqual(scheduled_run_key(datetime(2026,10,18,12,59,tzinfo=zone)),'2026-10-18-09')
        self.assertEqual(scheduled_run_key(datetime(2026,10,18,8,59,tzinfo=zone)),'2026-10-17-18')
