import copy,hashlib,json,unittest
from unittest.mock import patch
from kcee.regional_verification import parse,differences,verify,MAX_BYTES
from kcee.provenance import IntegrityError
class RegionalVerificationTests(unittest.TestCase):
 def fixture(self):return {'schema':'native-regional-loads-v1','report_run_id':'report','report_manifest_sha256':'a'*64,'native_archive_sha256':'b'*64,'implementation_sha256':'c'*64,'cases':[{'run_id':'source','manifest_sha256':'d'*64,'source_checks':{'mesh':True},'bore_checks_pass':True,'loads':{'x':1.25}}],'checks':{'ok':True},'limits':['sensitivity only']}
 def test_strict_parser_rejects_duplicate_nonfinite_and_oversized_data(self):
  self.assertEqual(parse(json.dumps(self.fixture()).encode()),self.fixture())
  for raw in [b'{"schema":"native-regional-loads-v1","schema":"native-regional-loads-v1"}',b'{"schema":"native-regional-loads-v1","v":NaN}',b'{"schema":"native-regional-loads-v1","v":1e999}',b'[]',b'{}',bytes([255]),b'x'*(MAX_BYTES+1),b'['*1000+b']'*1000]:
   with self.subTest(raw=raw[:50]),self.assertRaises(ValueError):parse(raw)
 def test_whole_snapshot_comparison_catches_metadata_and_boolean_type_changes(self):
  d=self.fixture();self.assertEqual(differences(d,copy.deepcopy(d)),[])
  for key,value in [('checks',{'ok':1}),('limits',[]),('implementation_sha256','changed'),('cases',[])]:
   self.assertEqual(differences({**d,key:value},d),[key])
  self.assertIn('unexpected_fields',differences({**d,'extra':1},d))
 def test_matching_snapshot_binds_exact_file_hash_and_sources(self):
  d=self.fixture();raw=json.dumps(d).encode()
  with patch('kcee.regional_forces.audit',return_value=d) as audit:result=verify('/unused','report',None,raw)
  audit.assert_called_once();self.assertEqual(result['integrity'],'matches_reproduced_sources');self.assertEqual(result['file_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(result['source_manifests'],[{'run_id':'source','manifest_sha256':'d'*64}])
 def test_changed_load_is_not_accepted_even_if_total_shape_is_valid(self):
  d=self.fixture();changed=copy.deepcopy(d);changed['cases'][0]['loads']['x']+=.001
  with patch('kcee.regional_forces.audit',return_value=d):result=verify('/unused','report',None,json.dumps(changed).encode())
  self.assertEqual(result['integrity'],'snapshot_differs');self.assertEqual(result['mismatched_fields'],['cases'])
 def test_wrong_source_does_not_replay_unrelated_evidence(self):
  with patch('kcee.regional_forces.audit') as audit:result=verify('/unused','other',None,json.dumps(self.fixture()).encode())
  audit.assert_not_called();self.assertEqual(result['integrity'],'source_mismatch');self.assertEqual(result['source_evidence'],'not_checked')
 def test_unavailable_corrupt_and_failed_replays_are_distinct(self):
  for error,status in [(KeyError('missing'),'source_unavailable'),(IntegrityError('tamper'),'source_integrity_failed'),(ValueError('replay'),'source_replay_failed')]:
   with patch('kcee.regional_forces.audit',side_effect=error):r=verify('/unused','report',None,json.dumps(self.fixture()).encode())
   self.assertEqual(r['integrity'],status);self.assertEqual(r['source_evidence'],'not_checked')
 def test_matching_snapshot_preserves_failed_original_engineering_gates(self):
  d=self.fixture();d['cases'][0]['bore_checks_pass']=False
  with patch('kcee.regional_forces.audit',return_value=d):r=verify('/unused','report',None,json.dumps(d).encode())
  self.assertEqual(r['integrity'],'matches_reproduced_sources');self.assertFalse(r['all_source_solver_checks']);self.assertEqual(r['engineering_acceptance'],'pending')
