import unittest,tempfile,math
from pathlib import Path
from kcee.openfoam_vortex import exact,make_case,field_values,metrics,summarize
class OpenFOAMVortexTests(unittest.TestCase):
 def test_analytical_solution_satisfies_momentum_and_continuity(self):
  x,y,t=.7,1.1,.3;h=1e-5;nu=.1;u,v,p=exact(x,y,t)
  dx=[(a-b)/(2*h) for a,b in zip(exact(x+h,y,t),exact(x-h,y,t))];dy=[(a-b)/(2*h) for a,b in zip(exact(x,y+h,t),exact(x,y-h,t))];dt=[(a-b)/(2*h) for a,b in zip(exact(x,y,t+h),exact(x,y,t-h))]
  self.assertAlmostEqual(dx[0]+dy[1],0,places=8)
  self.assertAlmostEqual(dt[0]+u*dx[0]+v*dy[0]+dx[2]+2*nu*u,0,places=8);self.assertAlmostEqual(dt[1]+u*dx[1]+v*dy[1]+dy[2]+2*nu*v,0,places=8)
 def test_pressure_gauge_and_field_metrics(self):
  n=16;values=[exact((i+.5)*2*math.pi/n,(j+.5)*2*math.pi/n,.5) for j in range(n) for i in range(n)]
  a=metrics(n,[(u,v,0) for u,v,p in values],[p+17 for u,v,p in values]);self.assertLess(a['relative_velocity_l2_error'],1e-14);self.assertLess(a['relative_pressure_l2_error'],1e-12);self.assertLess(a['relative_energy_error'],1e-12);self.assertLess(a['maximum_cell_central_divergence_s_inv'],1e-13)
  bad=metrics(n,[(u*.9,v*.9,0) for u,v,p in values],[p for u,v,p in values]);self.assertAlmostEqual(bad['relative_velocity_l2_error'],.1,places=10)
 def test_generated_case_is_bounded_and_initial_fields_parse(self):
  with tempfile.TemporaryDirectory() as tmp:
   make_case(tmp,16);self.assertEqual(len(field_values(Path(tmp)/'0/U',True)),256);self.assertEqual(len(field_values(Path(tmp)/'0/p')),256);self.assertIn('type cyclic',(Path(tmp)/'system/blockMeshDict').read_text());self.assertIn('pFinal',(Path(tmp)/'system/fvSolution').read_text())
   with self.assertRaises(ValueError):make_case(tmp,128)
   (Path(tmp)/'0/p').write_text('internalField nonuniform List<scalar> 2 (0);')
   with self.assertRaises(ValueError):field_values(Path(tmp)/'0/p')
 def test_failed_accuracy_and_refinement_never_pass(self):
  row={'relative_velocity_l2_error':.1,'relative_pressure_l2_error':.2,'relative_energy_error':.1,'maximum_local_continuity_error':1e-3,'mesh_check_passed':False}
  result=summarize([dict(row),dict(row)]);self.assertFalse(any(result['checks'].values()));self.assertEqual(result['validation_status'],'cfd_vortex_numerical_checks_failed')
 def test_solver_archive_rejects_changed_case_and_unsafe_names(self):
  import io,zipfile,json,base64,hashlib
  from kcee.vortex_run import verify_payload
  runtime={'package':'1912.200626-3+b1','architecture':'arm64','binaries_sha256':{name:'a'*64 for name in ('blockMesh','checkMesh','icoFoam')}}
  def payload(raw):return {'archive_base64':base64.b64encode(raw).decode(),'archive_sha256':hashlib.sha256(raw).hexdigest()}
  with tempfile.TemporaryDirectory() as tmp:
   make_case(tmp,16);buffer=io.BytesIO()
   with zipfile.ZipFile(buffer,'w') as z:
    z.writestr('runtime.json',json.dumps(runtime))
    for p in Path(tmp).rglob('*'):
     if p.is_file():z.writestr('16/'+p.relative_to(tmp).as_posix(),p.read_bytes() if p.name!='controlDict' else b'changed settings')
   with self.assertRaisesRegex(ValueError,'Unexpected solver case configuration'):verify_payload(payload(buffer.getvalue()))
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w') as z:z.writestr('../escape','x')
  with self.assertRaisesRegex(ValueError,'Unsafe solver archive'):verify_payload(payload(buffer.getvalue()))
