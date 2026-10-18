import unittest
from content_layout import threads_layout, blog_section,validate_emoji

class LayoutTests(unittest.TestCase):
    def test_threads_splits_dense_copy(self):
        text=threads_layout('정리함도 놓을 자리가 필요해. 선반 깊이를 먼저 재보자. 구성은 필요한 만큼 골라.')
        self.assertIn('\n\n✅ ',text);self.assertIn('\n· ',text)
    def test_existing_emoji_not_duplicated(self):
        text=threads_layout('선반 앞에서 막히기 전에.\n\n📌 깊이를 재보자.\n· 높이도 확인하자.')
        self.assertEqual(text.count('📌'),1);self.assertNotIn('✅',text)
    def test_decimal_not_split_and_blog_paragraphs(self):
        heading,blocks=blog_section('구성을 확인해요','3.2L 구성인지 확인해요. 놓을 자리를 재봐요.',1)
        self.assertTrue(heading.startswith('📌'));self.assertEqual(len(blocks),2);self.assertIn('3.2L',blocks[0])
    def test_excess_emoji_rejected(self):
        with self.assertRaises(ValueError):validate_emoji('✅✅✅',2)
        with self.assertRaises(ValueError):validate_emoji('🔥 지금',2)
