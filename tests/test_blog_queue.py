import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from blog_queue import prepare, enqueue, claim, finish

class BlogQueueTests(unittest.TestCase):
    def draft(self):
        return {'provider':'coupang','product':{'id':'123','name':'팬트리 수납함 3개','affiliateUrl':'https://link.coupang.com/a/test','option':'3개','image':'https://thumbnail.coupangcdn.com/test.jpg','imageVerifiedByOwner':True,'checkedAt':datetime.now(timezone.utc).isoformat()},'title':'팬트리 정리 전에 살펴볼 공간의 기준','sections':[{'heading':'놓을 자리부터 정해요','body':'수납함을 고르기 전에 선반에 놓을 물건을 나눠요. 자주 꺼내는 물건이 앞에 놓이는지 살펴보면 정리 순서를 정하기 좋아요. 손이 닿는 위치도 함께 생각해요.'},{'heading':'구성은 필요한 만큼','body':'묶음 구성은 편하지만 남는 수납함도 보관할 자리가 필요해요. 쓰려는 구역을 먼저 정하고 필요한 구성을 살펴요. 이미 쓰는 바구니와 겹치는 역할이 없는지도 확인해요.'},{'heading':'깊이와 높이를 함께 봐요','body':'선반의 깊이에 맞더라도 위쪽 공간이 부족하면 꺼내기 불편해요. 물건을 넣었을 때 손이 들어갈 여유도 함께 재봐요. 문을 닫거나 다른 물건을 꺼내는 데 방해가 없는지 살펴요.'}]}
    def test_pass_and_no_duplicate_publication(self):
        d=self.draft();self.assertEqual(prepare(d)['imagePosition'],'last')
        self.assertIn('<a href="https://link.coupang.com/a/test">',prepare(d)['html'])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'q.db';key=enqueue(d,'2026-10-18-10',path)
            with self.assertRaises(sqlite3.IntegrityError):enqueue(d,'2026-10-18-10',path)
            self.assertEqual(claim(key,path)['title'],d['title'])
            with self.assertRaises(ValueError):claim(key,path)
            finish(key,'https://blog.naver.com/sallim-select/123',path)
    def test_unverified_claim_and_stale_image_fail(self):
        for kind in ['claim','age','image']:
            d=self.draft()
            if kind=='claim':d['sections'][0]['body']+=' 폭이 99cm예요.'
            if kind=='age':d['product']['checkedAt']=(datetime.now(timezone.utc)-timedelta(hours=7)).isoformat()
            if kind=='image':d['product']['imageVerifiedByOwner']=False
            with self.assertRaises(ValueError):prepare(d)

    def test_verified_price_is_rendered_separately_from_generated_copy(self):
        d=self.draft();d['product'].update(price=6360,priceVerifiedByOwner=True,shipping=0,shippingVerifiedByOwner=True)
        result=prepare(d)
        self.assertIn('<b>6,360원</b>',result['html'])
        self.assertIn('3개 · 무료배송</span><br>',result['html'])
        self.assertNotIn('<!--verified-price-summary-->',result['html'])
        self.assertIn('배송비 무료',result['text'])
        self.assertIn('옵션 3개',result['text'])
        d['product']['priceVerifiedByOwner']=False
        self.assertNotIn('6,360원',prepare(d)['text'])
        d['product'].update(priceVerifiedByOwner=True,price=-1)
        with self.assertRaises(ValueError):prepare(d)
