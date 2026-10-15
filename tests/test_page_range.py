import unittest
from kcee.page_range import validate_page_range
class PageRangeTests(unittest.TestCase):
 def test_optional_and_bounded_ranges(self):
  self.assertIsNone(validate_page_range(None,None,None));self.assertEqual(validate_page_range('id',2,3),{'start':2,'end':3})
  for doc,start,end in [(None,1,2),('id',None,2),('id',3,2),('id',True,2),('id',1,301),('id','1',2)]:
   with self.assertRaises(ValueError):validate_page_range(doc,start,end)
