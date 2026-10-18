import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from tempfile import TemporaryDirectory
from operator_dashboard import next_slot, safe_link, snapshot, render, rows

class OperatorTests(unittest.TestCase):
    def test_next_slot_korean_midnight(self):
        now=datetime(2026,10,18,20,tzinfo=ZoneInfo('Asia/Seoul'))
        self.assertEqual(next_slot(now,[9,13,18]),'10/19 09:00')
    def test_external_and_script_links_are_rejected(self):
        self.assertEqual(safe_link('javascript:alert(1)','bad'),'')
        self.assertEqual(safe_link('https://blog.naver.com.evil.test/','bad'),'')
        self.assertIn('noopener',safe_link('https://blog.naver.com/sallim-select/123','글'))
    def test_missing_database_is_not_created(self):
        with TemporaryDirectory() as temp:
            db=Path(temp)/'missing.db';self.assertEqual(rows(db,'select 1'),[]);self.assertFalse(db.exists())
    def test_credentials_never_enter_rendered_output(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);(root/'.env').write_text('THREADS_ACCESS_TOKEN=DO_NOT_RENDER_THIS\nTHREADS_TOKEN_EXPIRES_AT=1797429997\n')
            view=render(snapshot(root))
            self.assertNotIn('DO_NOT_RENDER_THIS',view)
            self.assertIn('새 발행 대기열에 저장된 글이 없습니다',view)
    def test_malicious_title_escaped(self):
        with TemporaryDirectory() as temp:
            data=snapshot(Path(temp));data['threads']=[dict(status='draft_ready',updated=0,publication={},draft={'threadsPost':'<script>bad</script>'},product_name='<img src=x onerror=alert(1)>')]
            view=render(data);self.assertNotIn('<script>bad</script>',view);self.assertIn('&lt;script&gt;',view)

    def test_manual_posts_do_not_count_as_scheduled(self):
        with TemporaryDirectory() as temp:
            now=datetime(2026,10,18,16,tzinfo=ZoneInfo('Asia/Seoul'))
            data=snapshot(Path(temp),now);data['threadsHours']=[9,13,18]
            data['threads']=[dict(run_key=key,status='published',updated=now.timestamp(),publication={},draft={},product_name='상품') for key in ['2026-10-18-09','2026-10-18-13',None]]
            view=render(data)
            self.assertIn('2 / 3',view);self.assertIn('수동·시험 1건 별도',view)

    def test_manual_blog_records_separate_from_today(self):
        with TemporaryDirectory() as temp:
            data=snapshot(Path(temp));data['legacyBlogs']=[{'url':'https://blog.naver.com/sallim-select/1','status':'published_verified','title':'수동 글'},{'url':'https://blog.naver.com/sallim-select/1','status':'published_verified','title':'중복 기록'}]
            view=render(data)
            self.assertIn('수동 1건 누적',view)
            self.assertIn('오늘 블로그 예약 발행',view)

    def test_manual_comparison_excluded_from_reserved_count(self):
        with TemporaryDirectory() as temp:
            now=datetime(2026,10,18,20,tzinfo=ZoneInfo('Asia/Seoul'))
            data=snapshot(Path(temp),now)
            data['queue']=[{'state':'published','slot':slot,'public_url':'https://blog.naver.com/sallim-select/'+str(i),'payload':{}} for i,slot in enumerate(['2026-10-18-manual-comparison','2026-10-18-19'])]
            view=render(data)
            self.assertIn('1 / 2',view)
            self.assertIn('수동 1건 누적',view)
