import unittest
from datetime import datetime, timezone, timedelta
from content_quality import validate_copy, validate_threads_ready

class QualityTests(unittest.TestCase):
    def test_specs_and_general_advice(self):
        validate_copy('놓을 공간의 가로와 깊이를 먼저 재보자.', '수납함 3개')
        validate_copy('3개 구성이야.', '수납함 3개')
        with self.assertRaises(ValueError):validate_copy('폭이 30cm야.', '수납함 3개')
    def test_repetition_and_experience(self):
        for text in ['선반의 높이를 먼저 확인하는 게 좋겠어.\n선반의 높이를 먼저 확인하는 게 좋겠어.', '직접 사용해보니 편했어.', '가격은 9,900원이야.']:
            with self.assertRaises(ValueError):validate_copy(text, '수납함')
    def test_publication_gate(self):
        now=datetime.now(timezone.utc)
        draft={'threadsPost':'수납함\nhttps://link.coupang.com/a/test\n광고고지','productName':'수납함','deeplink':'https://link.coupang.com/a/test','productImage':'https://thumbnail.coupangcdn.com/image/test.jpg','priceCapturedAt':now.isoformat()}
        validate_threads_ready(draft,'광고고지',now)
        for update in [{'priceCapturedAt':(now-timedelta(hours=7)).isoformat()},{'threadsPost':'고지 없음'},{'productImage':''},{'deeplink':'https://link.coupang.com.evil.test/a/test'}]:
            with self.assertRaises(ValueError):validate_threads_ready({**draft,**update},'광고고지',now)
