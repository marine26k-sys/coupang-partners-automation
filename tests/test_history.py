from pathlib import Path
import tempfile
import unittest
from publication_history import History

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.history=History(Path(self.folder.name)/'history.sqlite3')
        self.product={'productId':1,'productName':'정리함'}

    def test_blocks_same_id_and_name_but_selects_new_product(self):
        key,_=self.history.reserve([self.product],'수납')
        self.history.update(key,'published')
        _,product=self.history.reserve([self.product,{'productId':2,'productName':'정리함'},
                                      {'productId':3,'productName':'다른 상품'}],'수납')
        self.assertEqual(product['productId'],3)

    def test_generation_failure_can_retry_but_uncertain_publish_cannot(self):
        key,_=self.history.reserve([self.product],'수납')
        self.history.update(key,'generation_failed',error_type='ValueError')
        key2,_=self.history.reserve([self.product],'수납')
        self.assertIsNotNone(key2)
        self.history.update(key2,'publication_uncertain')
        self.assertEqual(self.history.reserve([self.product],'수납'),(None,None))

    def test_old_product_can_be_selected_after_cooldown(self):
        self.history.reserve([self.product],'수납')
        with self.history.db() as db:
            db.execute('UPDATE runs SET created=created-31*86400')
        self.assertIsNotNone(self.history.reserve([self.product],'수납')[0])

    def test_history_keeps_each_draft_and_escapes_html(self):
        key,_=self.history.reserve([self.product],'수납')
        self.history.update(key,'published',draft={'threadsPair':{'body':'<script>x</script>','reply':'댓글'}},publication={'permalink':'https://www.threads.com/@test/post/x'})
        text=self.history.export_html().read_text()
        self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>',text)
        self.assertEqual(self.history.records()[0]['draft']['threadsPair']['reply'],'댓글')

    def test_keyword_rotation_and_import_is_idempotent(self):
        self.history.import_existing('old',self.product,{}, {})
        self.history.import_existing('old',self.product,{}, {})
        self.assertEqual(len(self.history.records()),1)
        self.history.reserve([{'productId':2,'productName':'상품2'}],'수납')
        self.assertEqual(self.history.next_keyword(['수납','주방']),'주방')
