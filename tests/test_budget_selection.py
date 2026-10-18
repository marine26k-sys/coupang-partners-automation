import unittest
from product_selection import prefer_budget

class BudgetSelectionTests(unittest.TestCase):
    def test_budget_boundaries_and_stable_fallback(self):
        products=[{'productPrice':30001},{'productPrice':10000},{'productPrice':0},{'productPrice':30000},{'productPrice':None}]
        self.assertEqual(prefer_budget(products,9),[products[1],products[0],products[2],products[3],products[4]])
        self.assertEqual(prefer_budget(products,13),[products[1],products[3],products[0],products[2],products[4]])
        self.assertEqual(prefer_budget(products,18),products)
    def test_no_budget_stock_preserves_candidates(self):
        products=[{'productPrice':40000},{'productPrice':50000}]
        self.assertEqual(prefer_budget(products,9),products)
