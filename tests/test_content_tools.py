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

    def test_candidate_fields_and_actual_age_buckets(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            h=History(Path(folder)/'test.sqlite3')
            h.save_candidates([{'productId': '42','productName':'<정리함>', 'productPrice':12000,
                                'productUrl':'secret-tracking','isRocket':True}], '수납')
            h.import_existing('x',{'productId':'42','productName':'정리함'}, {}, {'post_id':'1'})
            identifier=h.records()[0]['id']
            with h.db() as db:
                db.execute('INSERT INTO insight_samples VALUES(?,?,?,?)',
                           (identifier,100000+25*3600,100000,json.dumps({'views':123})))
                stored=db.execute('SELECT product FROM candidates').fetchone()[0]
                self.assertNotIn('secret-tracking',stored)
            text=h.export_html(Path(folder)/'report.html').read_text()
            self.assertIn('실제 25.0시간 후 조회 123',text)
            self.assertIn('48시간 구간: 기록 없음',text)
            self.assertIn('&lt;정리함&gt;',text)
            self.assertIn('12,000원',text)
