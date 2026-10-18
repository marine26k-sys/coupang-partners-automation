from datetime import datetime, timezone, timedelta
import unittest
from catalog_guard import check_count, price_anomaly
from marketplace_compare import compare
from growth_analytics import aggregate, fetch_reports, prefer_learned
from content_packages import bundle

class GrowthTests(unittest.TestCase):
    def test_count_and_price_guard(self):
        with self.assertRaises(ValueError):check_count(5,20)
        check_count(12,20)
        self.assertIsNotNone(price_anomaly(1000,10000))
        self.assertIsNone(price_anomaly(9000,10000))
    def test_reports_do_not_double_count_clicks(self):
        snapshot={'start':'20261001','end':'20261007','reports':{'clicks':{'available':True,'rows':[{'subId':'sallimthreads','click':5}]},'orders':{'available':False,'rows':[]},'cancels':{'available':True,'rows':[]},'commission':{'available':True,'rows':[{'subId':'sallimthreads','click':5,'commission':100}]}}}
        report=aggregate(snapshot);self.assertEqual(report['channels']['Threads']['clicks'],5);self.assertFalse(report['availability']['orders']);self.assertNotIn('orders',report['channels']['Threads'])
    def test_failed_report_is_unavailable_not_zero(self):
        class Client:
            def _request(self,*a,**kw):raise RuntimeError()
        result=fetch_reports(Client(),'20261001','20261007',pause=lambda x:None)
        self.assertTrue(all(not x['available'] for x in result['reports'].values()))
    def offer(self, service):
        return dict(service=service,name='수납함',brand='브랜드',model='모델',variant='화이트',quantity=3,unit='개',price=10000,shipping=None,verified=True,ownerLinkVerified=True,url='https://link.coupang.com/a/test' if service=='coupang' else 'https://toss.shopping/_m/test',checkedAt=datetime.now(timezone.utc).isoformat())
    def test_comparison_requires_exact_configuration_and_freshness(self):
        a=self.offer('coupang');b=self.offer('toss');result=compare([a,b]);self.assertEqual(len(result),1);self.assertFalse(result[0]['totalComparable'])
        b['quantity']=4;self.assertEqual(compare([a,b]),[])
        b['checkedAt']=(datetime.now(timezone.utc)-timedelta(hours=7)).isoformat()
        with self.assertRaises(ValueError):compare([a,b])
    def test_bundle_total_and_stale_exclusion(self):
        stamp=datetime.now(timezone.utc).isoformat();products=[dict(id=str(i),name='상품'+str(i),category='주방',price=4000,url='https://link.coupang.com/a/test',observedAt=stamp) for i in range(4)]
        products[0]['stale']=True
        result=bundle(products,budget=9000);self.assertEqual(result['displayPriceTotal'],8000);self.assertNotIn('0',result['productIds']);self.assertTrue(result['notCheckoutTotal'])
    def test_learning_small_samples_preserves_order(self):
        products=[{'selectionSource':'주방용품 베스트'},{'selectionSource':'생활용품 베스트'}]
        self.assertEqual(prefer_learned(products,{'groups':{'topic':{'주방용품 베스트':{'eligible':False}}}}),products)

    def test_rate_limit_stops_remaining_report_calls(self):
        import requests
        class Client:
            calls=0
            def _request(self,*a,**kw):
                self.calls+=1
                response=requests.Response();response.status_code=429
                raise requests.HTTPError(response=response)
        client=Client();result=fetch_reports(client,'20261001','20261007',pause=lambda x:None)
        self.assertEqual(client.calls,1)
        self.assertEqual(len(result['reports']),4)
        self.assertTrue(all(not r['available'] for r in result['reports'].values()))
