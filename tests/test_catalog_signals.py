import sqlite3
import unittest
from catalog_signals import enrich,recommendations
class SignalsTests(unittest.TestCase):
 def test_actual_days_and_option_isolation(self):
  db=sqlite3.connect(':memory:');self.addCleanup(db.close)
  db.execute('CREATE TABLE prices(id,option,day,price)');db.execute('CREATE TABLE ranks(category,id,day,rank)')
  db.executemany('INSERT INTO prices VALUES(?,?,?,?)',[('1','a','2026-10-17',100),('1','a','2026-10-18',90),('1','b','2026-10-16',10)])
  p={'id':'1','category':'주방','price':90,'priceChange':-10,'previousPrice':100}
  score=enrich(db,p,'a','2026-10-18');p['recommendScore']=score
  self.assertEqual(p['observedLow'],90);self.assertEqual(p['observationDays'],2)
  self.assertIn('10원 하락',recommendations([p])[0]['reasons'][0])
 def test_stale_products_never_recommended(self):
  self.assertEqual(recommendations([{'id':'1','stale':True}]),[])
