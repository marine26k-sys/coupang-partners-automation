import unittest
from blog_drafts import compose,TOSS_DISCLOSURE
from content_generator import DISCLOSURE_TEXT
class BlogDraftTests(unittest.TestCase):
 def test_provider_disclosures_and_verified_toss_link(self):
  p={'name':'수납함','affiliateUrl':'https://toss.shopping/_m/example','linkVerifiedByOwner':True}
  d=compose(p,'toss');self.assertTrue(d['text'].startswith(TOSS_DISCLOSURE));self.assertNotIn(DISCLOSURE_TEXT,d['text'])
 def test_unverified_or_wrong_provider_link_is_rejected(self):
  with self.assertRaises(ValueError):compose({'name':'상품','affiliateUrl':'https://toss.shopping/_m/example'},'toss')
  with self.assertRaises(ValueError):compose({'name':'상품','affiliateUrl':'https://link.coupang.com/a/example'},'toss')
 def test_unverified_price_not_presented_as_current(self):
  d=compose({'name':'<상품>','affiliateUrl':'https://link.coupang.com/a/example','price':100},'coupang')
  self.assertNotIn('100원',d['text']);self.assertIn('&lt;상품&gt;',d['html']);self.assertEqual(d['status'],'draft_only')
