from datetime import datetime,timezone
import unittest
from comparison_editorial import build, quantity

class ComparisonEditorialTests(unittest.TestCase):
    def products(self):
        return [dict(id=str(i),name=f'정리함{i}, 화이트, {i+2}개',category='수납',price=10000,url='https://link.coupang.com/a/test',optionKey=str(i),observedAt=datetime.now(timezone.utc).isoformat()) for i in range(3)]
    def test_verified_quantities_and_rounding(self):
        result=build(self.products());self.assertEqual(result['products'][1]['unitPrice'],3333);self.assertTrue(result['noPerformanceRanking']);self.assertIn('직접 사용한 후기',result['text'])
    def test_quantity_missing_not_inferred(self):
        self.assertIsNone(quantity('정리함 L'));self.assertEqual(quantity('정리함, 5개'),5)
        products=self.products();products[0]['name']='수량 미제공';products[1]['stale']=True
        with self.assertRaises(ValueError):build(products)
    def test_duplicates_and_review_flags_excluded(self):
        products=self.products();products[1]['id']=products[0]['id'];products[2]['reviewReason']='급변'
        with self.assertRaises(ValueError):build(products)
