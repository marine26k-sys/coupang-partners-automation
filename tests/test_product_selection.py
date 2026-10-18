import unittest
from unittest.mock import Mock
from product_selection import ranked_candidates

class RankedSelectionTests(unittest.TestCase):
    def test_source_rotation_and_api_order_are_preserved(self):
        client=Mock();history=Mock();history.next_keyword.return_value='주방용품 베스트'
        client._request.side_effect=[{'data':[{'productId':2,'productName':'주방 A'},{'productId':1,'productName':'주방 B'}]},
                                   {'data':[{'productId':3,'productName':'골드박스'}]},
                                   {'data':[{'productId':4,'productName':'생활'}]}]
        products,source=ranked_candidates(client,history)
        self.assertEqual(source,'주방용품 베스트')
        self.assertEqual([p['productId'] for p in products],[2,1,3,4])
        self.assertEqual(products[0]['selectionRank'],1)
        client.search_products.assert_not_called()

    def test_failed_source_falls_back_only_to_official_list(self):
        client=Mock();history=Mock();history.next_keyword.return_value='골드박스'
        client._request.side_effect=[RuntimeError('failed'),{'data':[{'productId':1,'productName':'정리함'}]}, {'data':[]}]
        products,_=ranked_candidates(client,history)
        self.assertEqual(products[0]['selectionSource'],'주방용품 베스트')
        client.search_products.assert_not_called()

    def test_all_sources_failed_stops_without_search(self):
        client=Mock();history=Mock();history.next_keyword.return_value='골드박스'
        client._request.side_effect=RuntimeError('failed')
        with self.assertRaises(RuntimeError):ranked_candidates(client,history)
        client.search_products.assert_not_called()
