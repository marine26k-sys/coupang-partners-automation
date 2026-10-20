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

class ThreadsPairTests(unittest.TestCase):
    def test_reply_targets_published_root_and_retry_does_not_duplicate(self):
        from threads_api import publish_pair
        from content_generator import SHORT_DISCLOSURE
        with tempfile.TemporaryDirectory() as folder:
            client = Mock(user_id='account-1')
            client.request.side_effect = [
                {'id':'root-container'}, {'id':'root-post'}, {'permalink':'root-url'},
                {'id':'reply-container'}, {'id':'reply-post'}, {'permalink':'reply-url'}]
            pair = {'body':SHORT_DISCLOSURE+'\n구매 전에 어떤 구성을 확인해?', 'reply':TEXT}
            path = Path(folder)/'posts.sqlite3'
            result = publish_pair(pair,'slot',client,path)
            self.assertEqual(result['reply_id'],'reply-post')
            self.assertEqual(client.request.call_args_list[3].args[2]['reply_to_id'],'root-post')
            publish_pair(pair,'slot',client,path)
            self.assertEqual(client.request.call_count,6)

    def test_bad_reply_prevents_root_publication(self):
        from threads_api import publish_pair
        from content_generator import SHORT_DISCLOSURE
        client = Mock(user_id='account-1')
        with self.assertRaises(ThreadsError):
            publish_pair({'body':SHORT_DISCLOSURE+'\n질문', 'reply':'고지 없는 링크'},client=client)
        client.request.assert_not_called()

class BrandVoiceTests(unittest.TestCase):
    def test_forbidden_hype_is_blocked(self):
        from unittest.mock import patch
        from content_generator import generate_threads_pair
        with patch('content_generator.TextModel.generate_content',return_value=Mock(text='{"hook":"무조건 사야 해!", "reply":"정리함이야."}')):
            with self.assertRaises(ValueError):
                generate_threads_pair('정리함','https://link.coupang.com/a/test')

    def test_voice_instructions_are_loaded_into_generation(self):
        from unittest.mock import patch
        from content_generator import generate_threads_pair
        with patch('content_generator.TextModel') as model:
            model.return_value.generate_content.return_value = Mock(text='{"hook":"수납함도 놓을 자리가 먼저지.\\n폭부터 재보면 고르기 쉽겠어.","reply":"다용도 팬트리 정리함이야."}')
            pair = generate_threads_pair('정리함','https://link.coupang.com/a/test')
        self.assertIn('가짜 대화',model.call_args.args[0])
        self.assertIn('수납함도 놓을 자리가',pair['body'])

class SingleBodyTests(unittest.TestCase):
    def test_body_has_product_link_and_disclosure_without_comment(self):
        from content_generator import build_threads_post, SHORT_DISCLOSURE
        text=build_threads_post('앞으로 당길 공간도 재보고 골라.','슬라이딩 정리함','https://link.coupang.com/a/test')
        self.assertTrue(text.startswith('앞으로 당길 공간도 재보고 골라\n'))
        self.assertEqual(text.count(DISCLOSURE_TEXT),1)
        self.assertNotIn(SHORT_DISCLOSURE,text)
        self.assertTrue(text.endswith('※ '+DISCLOSURE_TEXT))
        self.assertIn('슬라이딩 정리함',text)
        self.assertIn('https://link.coupang.com/a/test',text)
        self.assertNotIn('댓글',text)

    def test_comment_directions_are_rejected(self):
        from content_generator import build_threads_post
        with self.assertRaises(ValueError):
            build_threads_post('첫 댓글을 확인해.','정리함','https://link.coupang.com/a/test')

class ContainerReadinessTests(unittest.TestCase):
    def test_waits_until_finished_before_returning(self):
        from unittest.mock import patch
        from threads_api import ThreadsClient
        client=ThreadsClient(token='test',user_id='test')
        client.request=Mock(side_effect=[{'status':'IN_PROGRESS'},{'status':'FINISHED'}])
        with patch('threads_api.time.sleep') as sleep:
            client.wait_ready('container')
        self.assertEqual(client.request.call_count,2)
        sleep.assert_called_once_with(1)

class GenerationRepairTests(unittest.TestCase):
    def test_invalid_specs_are_rewritten_before_publishing(self):
        from unittest.mock import patch
        from content_generator import generate_threads_post
        with patch('content_generator.TextModel') as model:
            model.return_value.generate_content.side_effect=[Mock(text='폭이 99cm라 정리하기 좋아.'),Mock(text='선반에 놓을 정리함을 찾고 있어?\n필요한 개수를 정해봐.')]
            text=generate_threads_post('정리함','https://link.coupang.com/a/test')
        self.assertNotIn('99cm',text)
        self.assertEqual(model.return_value.generate_content.call_count,2)
    def test_repeated_bad_copy_still_fails_closed(self):
        from unittest.mock import patch
        from content_generator import generate_threads_post
        with patch('content_generator.TextModel') as model:
            model.return_value.generate_content.return_value=Mock(text='폭이 99cm라 정리하기 좋아.')
            with self.assertRaises(ValueError):generate_threads_post('정리함','https://link.coupang.com/a/test')
            self.assertEqual(model.return_value.generate_content.call_count,3)
