import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import catalog

class CatalogTest(unittest.TestCase):
    def test_only_public_fields_and_own_links(self):
        class Client:
            def search_products(self,keyword,limit):
                return [{'productId':42,'productName':'수납함','productPrice':12000,
                    'productUrl':'https://www.coupang.com/vp/products/42?vendorItemId=99&lptag=OTHER',
                    'productImage':'https://ads-partners.coupang.com/image1/example','secret':'NEVER'}]
            def _request(self,*args,**kwargs):return {'data':self.search_products('',8)}
            def create_deeplinks(self,urls,sub_id):
                assert all('OTHER' not in u for u in urls)
                assert len(urls)<=5
                return [{'originalUrl':u,'shortenUrl':'https://link.coupang.com/a/ours'} for u in urls]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);public=root/'public'
            with patch.object(catalog,'ROOT',root),patch.object(catalog,'PUBLIC',public),patch.object(catalog,'CoupangPartnersClient',Client):
                self.assertEqual(catalog.collect(),4)
                result=(public/'catalog.json').read_text()
                self.assertNotIn('NEVER',result)
                self.assertNotIn('OTHER',result)
                data=json.loads(result)
                self.assertEqual(data['products'][0]['url'],'https://link.coupang.com/a/ours')
                self.assertIsNone(data['products'][0]['priceChange'])

    def test_failed_collection_preserves_previous_public_data(self):
        class Client:
            def search_products(self,*args,**kwargs):raise RuntimeError('private response')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);public=root/'public';public.mkdir()
            (public/'catalog.json').write_text('previous')
            with patch.object(catalog,'ROOT',root),patch.object(catalog,'PUBLIC',public),patch.object(catalog,'CoupangPartnersClient',Client):
                with self.assertRaises(RuntimeError):catalog.collect()
                self.assertEqual((public/'catalog.json').read_text(),'previous')
