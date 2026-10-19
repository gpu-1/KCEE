import io,json,math,tempfile,threading,unittest,zipfile
from pathlib import Path
from kcee.native_forces import boundary_values,native_vectors,integrate,pack,unpack,functions,validate_runtime
from kcee.cfd_control import Control,using,Cancelled

def runtime_record():
 return {'method':'openfoam-full-stress-v1','package':'1912.200626-3+b1','simpleFoam_sha256':'a'*64,'libraries_sha256':{n:'a'*64 for n in ('libOpenFOAM.so','libforces.so','libincompressibleTurbulenceModels.so','libincompressibleTransportModels.so')},'overlay':{'source_sha256':'c75ca0f04cc4f49708296c1926cbde9d0138b3fef298fed54270dfe29e2df404','scope':'dictionary::digest only; LD_PRELOAD only for native postprocessing','binaries_sha256':{'libkceeDigest.so':'b'*64,'hash-self-test':'c'*64},'implementation_sha256':{n:'d'*64 for n in ('build.py','digest.cpp','hash_test.cpp','exports.map')}}}

def evidence():
 def dat(total,pressure,viscous):
  vec=lambda v:'('+' '.join(map(str,v))+')'
  return ('# native fixture\n1500 '+vec(total)+' '+vec(pressure)+' '+vec(viscous)+'\n').encode()
 return {'wall-centres.foam':b'dimensions [0 1 0 0 0 0 0]; bottom {type calculated;value uniform (0.1 0 0.2);}', 'wall-stress.foam':b'dimensions [0 2 -2 0 0 0 0];bottom {type calculated;value uniform (0.1 0.2 0.3 -0.4 0.5 0.3);}', 'force.dat':dat([-.4,-5.2,-1],[0,-6,0],[-.4,.8,-1]),'moment.dat':dat([1.04,.02,-.52],[1.2,0,-.6],[-.16,.02,.08]),'postprocess.log':b'End\n','controlDict':b'fixed','runtime.json':json.dumps(runtime_record()).encode()}

class NativeForceTests(unittest.TestCase):
 def test_full_tensor_integral_includes_normal_viscous_traction(self):
  r=integrate(evidence(),[(0,0,[0,-1,0])],[3],2,1,1500)
  self.assertEqual(r['viscous_force_N'],[-.4,.8,-1]);self.assertEqual(r['pressure_force_N'],[0,-6,0]);self.assertTrue(all(r['checks'].values()));self.assertLess(r['independent_moment_replay_error_N_m'],1e-14)
 def test_changed_tensor_and_face_centres_are_rejected_by_native_replay(self):
  for key,value in [('wall-stress.foam',evidence()['wall-stress.foam'].replace(b'-0.4',b'-0.2')),('wall-centres.foam',evidence()['wall-centres.foam'].replace(b'0.1 0 0.2',b'0.3 0 0.2')),('wall-stress.foam',evidence()['wall-stress.foam'].replace(b'[0 2 -2',b'[1 2 -2'))]:
   files=evidence();files[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):integrate(files,[(0,0,[0,-1,0])],[3],2,1,1500)
 def test_boundary_field_count_components_and_nonfinite_values(self):
  self.assertEqual(boundary_values('value nonuniform List<vector> 2 ((1 2 3)(4 5 6));',2,3),[[1,2,3],[4,5,6]])
  for text,n in [('value uniform (nan 0 0);',1),('value uniform (1 2);',1),('value nonuniform List<vector> 2 ((1 2 3));',2)]:
   with self.assertRaises(ValueError):boundary_values(text,n,3)
 def test_native_vectors_require_one_time_and_exact_components(self):
  self.assertEqual(native_vectors(evidence()['force.dat'],1500)['viscous'],[-.4,.8,-1])
  for data in [evidence()['force.dat']+evidence()['force.dat'],evidence()['force.dat'].replace(b'1500',b'0'),evidence()['force.dat'].replace(b'-5.2',b'-5.1')]:
   with self.assertRaises(ValueError):native_vectors(data,1500)
 def test_archive_inventory_is_closed_and_bounded(self):
  self.assertEqual(unpack(pack(evidence())),evidence())
  files=evidence();files['../escape']=b'bad'
  with self.assertRaises(ValueError):unpack(pack(files))
 def test_runtime_rejects_missing_hashes_and_changed_overlay_scope(self):
  self.assertEqual(validate_runtime(runtime_record())['method'],'openfoam-full-stress-v1')
  for mutate in [lambda r:r['overlay'].update(scope='global bypass'),lambda r:r['overlay']['binaries_sha256'].pop('hash-self-test'),lambda r:r['libraries_sha256'].update({'libforces.so':'not-a-hash'})]:
   r=runtime_record();mutate(r)
   with self.assertRaises(ValueError):validate_runtime(r)
 def test_function_dictionary_rejects_arbitrary_patches(self):
  for patch in (';system(foo)','other'):
   with self.assertRaises(ValueError):functions(patch,1)
  self.assertIn('rhoInf 2;',functions('bracket',2));self.assertIn('fields (devReff)',functions('bottom',2))
 def test_native_integration_observes_job_cancellation(self):
  event=threading.Event();event.set()
  with using(Control(event)),self.assertRaises(Cancelled):integrate(evidence(),[(0,0,[0,-1,0])],[3],2,1,1500)
 def test_analytical_benchmark_has_nonzero_normal_viscous_force(self):
  from kcee.native_force_benchmark import exact,dictionaries
  r=exact();self.assertLess(r['viscous_force_N'][1],0);self.assertGreater(r['viscous_force_N'][0],0);self.assertNotEqual(r['viscous_moment_N_m'][2],0)
  with self.assertRaises(ValueError):dictionaries(1000)
 def test_native_job_uses_fixed_recipe(self):
  from kcee.cfd_jobs import validate
  import uuid
  validate('native_forces',str(uuid.uuid4()),{})
  with self.assertRaises(ValueError):validate('native_forces',str(uuid.uuid4()),{'arbitrary':'input'})
 def test_worker_rejects_executable_archive_directives(self):
  from kcee.native_forces import source_members
  names=['1500/U','1500/p','1500/phi','runtime.json']+['constant/polyMesh/'+n for n in ('points','faces','owner','neighbour','boundary')]+['constant/transportProperties','constant/turbulenceProperties','system/controlDict','system/fvSchemes','system/fvSolution']
  for bad in (b'#include "/etc/passwd"',b'type codedFixedValue;',b'\x00'):
   files={n:b'plain numeric fixture' for n in names};files['1500/U']=bad
   with self.assertRaisesRegex(ValueError,'plain numeric ASCII'):source_members(pack(files))
 def test_native_report_inventory_zip_hash_and_portable_restore(self):
  import uuid
  from kcee.native_forces_run import save
  from kcee.provenance import verify_directory,IntegrityError
  from kcee.run_backup import export_run,restore_run
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);parent=root/str(uuid.uuid4());parent.mkdir()
   for n in ('requirements.json','geometry.json','geometry-request.json'):(parent/n).write_text('{}')
   (parent/'bracket.stl').write_text('synthetic native inventory fixture')
   loads=integrate(evidence(),[(0,0,[0,-1,0])],[3],2,1,1500)
   prior={'viscous_estimate_force_N':[0,0,0]};row={'run_id':str(uuid.uuid4()),'manifest_sha256':'a'*64,'native_evidence_sha256':'b'*64,'mesh_name':'coarse','domain_name':'base','local_profile':'baseline','loads':loads,'prior_estimate':prior,'native_minus_estimate':{'viscous_force_N':loads['viscous_force_N']}}
   data={'studies':[row],'benchmark':{'fixture':True},'comparisons':[],'checks':{'fixture':True}}
   dest=save(root,parent.name,{'manifest_sha256':'c'*64},data,{'benchmark.zip':b'fixture',row['run_id']+'.zip':pack(evidence())});m,digest=verify_directory(dest)
   self.assertEqual(m['kind'],'bracket_flow_native_forces');self.assertIn('native-forces.zip',m['artifacts']);self.assertEqual(len((dest/'verification.csv').read_text().splitlines()),4)
   bundle=root/'native.zip';receipt=export_run(dest,bundle,digest);restore_parent=root/'restore';restore_parent.mkdir();restored=restore_run(bundle,restore_parent/dest.name,receipt['bundle_sha256'],digest);self.assertEqual(restored['manifest_sha256'],digest)
   (dest/'native-forces.zip').write_bytes(b'tamper')
   with self.assertRaises(IntegrityError):verify_directory(dest,expected_digest=digest)
