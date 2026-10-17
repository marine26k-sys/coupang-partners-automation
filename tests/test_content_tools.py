import tempfile
import unittest
from pathlib import Path
from publication_history import History
from content_tools import collect, rewrite


class ToolsTest(unittest.TestCase):
    def test_real_metrics_and_unpublished_rewrite(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder) / 'test.sqlite3')
            history.import_existing('test', {'productId':'1','productName':'정리함'},
                {'deeplink':'https://link.coupang.com/a/test'}, {'post_id':'123'})
            identifier = history.records()[0]['id']
            class Client:
                def verify_account(self): pass
                def request(self, method, path, data):
                    self.path = path
                    return {'data':[{'name':'views','values':[{'value':0}]}]}
            self.assertEqual(collect(history, Client()), 1)
            rewrite(history, identifier, lambda name, link: {'body':'새 본문','reply':link})
            with history.db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],1)
            self.assertEqual(history.records()[0]['status'],'published')
            page = history.export_html(Path(folder)/'report.html').read_text()
            self.assertIn('조회 0', page)
            self.assertIn('좋아요 미제공', page)
            self.assertIn('미발행 재작성 초안',page)

    def test_deleted_posts_are_not_fetched(self):
        with tempfile.TemporaryDirectory() as folder:
            history=History(Path(folder)/'test.sqlite3')
            history.import_existing('deleted',{'productId':'1','productName':'old'}, {}, {'post_id':'1'}, 'deleted')
            class Client:
                def verify_account(self): pass
                def request(self,*args): raise AssertionError('deleted post')
            self.assertEqual(collect(history,Client()),0)
