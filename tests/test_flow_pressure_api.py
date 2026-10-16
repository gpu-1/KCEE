"""Invalid bore-study input must be rejected before database or solver access."""
import importlib.util,unittest
from unittest.mock import patch
from uuid import UUID
@unittest.skipUnless(importlib.util.find_spec('app'),'API routes tested inside API image')
class BorePressureAPITests(unittest.TestCase):
 def test_invalid_inputs_rejected_before_readiness(self):
  from app import bracket_external_flow
  from fastapi import HTTPException
  invalid=[{'sampling_version':'unknown'},{'sampling_version':None},{'sampling_version':[]},{'bore_level':True},{'bore_level':4.0},{'bore_level':6},{'mesh_name':[]},{'domain_name':'unknown'},{'domain_name':'expanded','mesh_name':'coarse'},{'other':1}]
  with patch('app.ready',side_effect=AssertionError('Readiness must not be called')):
   for body in invalid:
    with self.subTest(body=body),self.assertRaises(HTTPException) as error:bracket_external_flow(UUID(int=1),body)
    self.assertEqual(error.exception.status_code,422)
