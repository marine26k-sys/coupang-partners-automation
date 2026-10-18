import unittest
from unittest.mock import Mock
from featured_products import featured_records

class FeaturedTests(unittest.TestCase):
    def test_only_public_successful_posts_are_exported(self):
        row={'id':'x','created':0,'status':'published','product_id':'1','product_name':'정리함','draft':{'deeplink':'https://link.coupang.com/a/ours','private':'secret'},'publication':{'permalink':'https://www.threads.com/@sallim.select/post/test','post_id':'p'}}
        h=Mock();h.records.return_value=[{**row,'status':'deleted'},row]
        result=featured_records(h)
        self.assertEqual(len(result),1)
        self.assertNotIn('secret',str(result))
        self.assertEqual(result[0]['number'],'X')
