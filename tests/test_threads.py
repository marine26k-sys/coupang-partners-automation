import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
from content_generator import DISCLOSURE_TEXT
from threads_api import ThreadsError, publish_text

TEXT = DISCLOSURE_TEXT + '\n상품명에 명시된 구성을 확인해보세요.\nhttps://link.coupang.com/a/test'


class ThreadsPublishingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.journal = Path(self.folder.name) / 'posts.sqlite3'
        self.client = Mock(user_id='account-1')
        self.client.request.side_effect = [
            {'id': 'container-1'}, {'id': 'post-1'},
            {'permalink': 'https://www.threads.com/@test/post/example'}]

    def test_publish_once_and_keep_same_slot_idempotent(self):
        first = publish_text(TEXT, 'slot-1', self.client, self.journal)
        second = publish_text(TEXT + '\n별도 생성된 문구', 'slot-1', self.client, self.journal)
        self.assertEqual(first['post_id'], second['post_id'])
        self.assertEqual(self.client.request.call_count, 3)

    def test_uncertain_publish_is_not_retried(self):
        self.client.request.side_effect = [{'id': 'container-1'}, ThreadsError('timeout')]
        with self.assertRaises(ThreadsError):
            publish_text(TEXT, 'slot-1', self.client, self.journal)
        with self.assertRaises(ThreadsError):
            publish_text(TEXT, 'slot-1', self.client, self.journal)
        self.assertEqual(self.client.request.call_count, 2)

    def test_oversize_is_rejected_before_any_network_request(self):
        with self.assertRaises(ThreadsError):
            publish_text(TEXT + '가' * 500, 'slot-1', self.client, self.journal)
        self.client.request.assert_not_called()

    def test_missing_disclosure_is_rejected_before_any_network_request(self):
        with self.assertRaises(ThreadsError):
            publish_text('상품 https://link.coupang.com/a/test', 'slot-1', self.client, self.journal)
        self.client.request.assert_not_called()

    def test_permalink_failure_does_not_duplicate_successful_post(self):
        self.client.request.side_effect = [
            {'id': 'container-1'}, {'id': 'post-1'}, ThreadsError('read error')]
        result = publish_text(TEXT, 'slot-1', self.client, self.journal)
        self.assertEqual(result['state'], 'published')
        self.assertEqual(publish_text(TEXT, 'slot-1', self.client, self.journal)['post_id'], 'post-1')
        self.assertEqual(self.client.request.call_count, 3)
