import unittest
from datetime import datetime,timezone,timedelta
from price_display import price_line,add_threads_price
class PriceDisplayTests(unittest.TestCase):
    def test_amount_and_korean_time_are_source_fields(self):
        now=datetime(2026,10,19,8,0,tzinfo=timezone.utc)
        self.assertEqual(price_line(6360,now.isoformat(),now),'표시가격 6,360원 · 10/19 17:00 기준')
        for amount in [0,-1,True,float('nan'),float('inf'),'6360']:
            with self.assertRaises(ValueError):price_line(amount,now.isoformat(),now)
        with self.assertRaises(ValueError):price_line(6360,(now-timedelta(hours=7)).isoformat(),now)
    def test_price_added_before_link_and_limit_enforced(self):
        stamp=datetime.now(timezone.utc).isoformat();link='https://link.coupang.com/a/test'
        text=add_threads_price('훅\n상품\n'+link+'\n고지',link,7990,stamp)
        self.assertLess(text.index('7,990원'),text.index(link))
        self.assertIn('고지',text)
        with self.assertRaises(ValueError):add_threads_price('가'*480+'\n'+link,link,7990,stamp)
