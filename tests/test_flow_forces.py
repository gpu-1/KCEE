import io,json,math,tempfile,threading,unittest,zipfile
from pathlib import Path
from kcee.flow_forces import face_geometry,face_load,benchmark,from_archive
from kcee.cfd_control import Control,using,Cancelled

def fixture():
 points=[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]]
 # Outward from external fluid into the solid.
 faces=[[0,3,7,4],[1,5,6,2],[0,4,5,1],[3,2,6,7],[0,1,2,3],[4,7,6,5]]
 fields=[]
 for face in faces:
  sf,c,ma=face_geometry([points[i] for i in face]);owner=[c[i]-sf[i]*.1 for i in range(3)]
  fields.append(dict(zip(('x_m','y_m','z_m','u_m_s','v_m_s','w_m_s','p_kinematic_m2_s2'),[*owner,0,0,0,7+2*c[0]-3*c[1]+4*c[2]])))
 fields+= [dict(fields[0]) for _ in range(1000-len(fields))]
 flow={'field':fields,'inputs':{'density_kg_m3':2.,'kinematic_viscosity_m2_s':.002,'inlet_velocity_m_s':.01}}
 mesh=lambda count,text:'FoamFile {}\n'+str(count)+'\n(\n'+text+'\n)\n'
 vec=lambda p:'('+' '.join(map(str,p))+')'
 files={'constant/polyMesh/points':mesh(8,'\n'.join(map(vec,points))),'constant/polyMesh/faces':mesh(6,'\n'.join(str(len(f))+vec(f) for f in faces)),'constant/polyMesh/owner':mesh(6,'0 1 2 3 4 5'),'constant/polyMesh/neighbour':mesh(0,''),'constant/polyMesh/boundary':'FoamFile {}\n1\n( bracket {type wall; nFaces 6; startFace 0;} )','1500/p':'dimensions [0 2 -2 0 0 0 0]; boundaryField { bracket {type zeroGradient;} }','1500/U':'boundaryField { bracket {type fixedValue;value uniform (0 0 0);} }'}
 return flow,files

def archive(files):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:
  for n,v in files.items():z.writestr(n,v)
 return b.getvalue()

class ForceTests(unittest.TestCase):
 def test_analytical_force_moment_and_wall_gradient_order(self):
  b=benchmark();self.assertTrue(all(b['checks'].values()));self.assertEqual(b['pressure_force_N'],[-4,6,-8]);self.assertEqual(b['pressure_moment_N_m'],[-7,2,5]);self.assertTrue(all(abs(v-1)<1e-12 for v in b['observed_orders']))
 def test_shear_units_sign_tangential_projection_and_density(self):
  r=face_load([0,-.02,0],[0,0,0],[0,.001,0],[2,3,0],5,1000,1e-6)
  self.assertEqual(r['pressure_N'],[0,-100,0]);self.assertAlmostEqual(r['viscous_estimate_N'][0],.04);self.assertEqual(r['viscous_estimate_N'][1],0)
 def test_reversed_wall_orientation_is_rejected(self):
  with self.assertRaises(ValueError):face_load([0,1,0],[0,0,0],[0,.1,0],[1,0,0],0,1,1)
 def test_nonfinite_and_nonpositive_physics_rejected(self):
  for rho,nu,p in [(0,1,0),(1,-1,0),(1,1,float('nan'))]:
   with self.assertRaises(ValueError):face_load([0,-1,0],[0,0,0],[0,.1,0],[1,0,0],p,rho,nu)
 def test_pressure_force_and_moment_replayed_from_closed_wall(self):
  flow,files=fixture();r=from_archive(archive(files),flow)
  self.assertEqual(r['pressure_force_N'],[-4,6,-8]);self.assertEqual(r['pressure_moment_N_m'],[-7,2,5]);self.assertEqual(r['viscous_estimate_force_N'],[0,0,0]);self.assertTrue(all(r['checks'].values()))
 def test_constant_pressure_shift_changes_neither_force_nor_moment(self):
  flow,files=fixture();a=from_archive(archive(files),flow)
  for f in flow['field']:f['p_kinematic_m2_s2']+=100
  b=from_archive(archive(files),flow)
  self.assertEqual(a['pressure_force_N'],b['pressure_force_N']);self.assertEqual(a['pressure_moment_N_m'],b['pressure_moment_N_m'])
 def test_archive_boundary_and_addressing_rejection(self):
  flow,files=fixture()
  for name,value in [('1500/p',files['1500/p'].replace('zeroGradient','fixedValue')),('1500/U',files['1500/U'].replace('(0 0 0)','(1 0 0)')),('constant/polyMesh/owner','FoamFile {}\n6\n(1001 1 2 3 4 5)'),('constant/polyMesh/boundary',files['constant/polyMesh/boundary'].replace('startFace 0','startFace 99')),('../escape','bad')]:
   changed=dict(files);changed[name]=value
   with self.subTest(name=name),self.assertRaises(ValueError):from_archive(archive(changed),flow)
 def test_wall_integration_observes_cancellation(self):
  flow,files=fixture();event=threading.Event();event.set()
  with using(Control(event)),self.assertRaises(Cancelled):from_archive(archive(files),flow)
 def test_warped_faces_keep_exact_oriented_area_moment(self):
  vertices=[[0,0,0],[1,0,0],[1,1,.2],[0,1,0]];sf,c,ma=face_geometry(vertices)
  # Independent two-triangle integral about origin, using a common diagonal.
  from kcee.flow_forces import cross,sub,scale
  expected=[0.,0.,0.]
  for a,b,d in [(vertices[0],vertices[1],vertices[2]),(vertices[0],vertices[2],vertices[3])]:
   t=scale(cross(sub(b,a),sub(d,a)),.5);centroid=[(a[k]+b[k]+d[k])/3 for k in range(3)];v=cross(centroid,t)
   expected=[expected[k]+v[k] for k in range(3)]
  # Different triangulations describe different warped surfaces, so do not
  # assert equality of their moments. Reversing our fan must negate both.
  reverse=face_geometry(list(reversed(vertices)))
  for a,b in zip(sf,reverse[0]):self.assertAlmostEqual(a,-b)
  for a,b in zip(ma,reverse[2]):self.assertAlmostEqual(a,-b)
  self.assertGreater(math.dist(ma,expected),0)
 def test_force_job_recipe_is_fixed(self):
  from kcee.cfd_jobs import validate
  import uuid
  validate('forces',str(uuid.uuid4()),{})
  with self.assertRaises(ValueError):validate('forces',str(uuid.uuid4()),{'density':1000})
 def test_comparisons_preserve_signed_changes_without_zero_denominators(self):
  from unittest.mock import patch
  from kcee.flow_forces_run import summarize,RECIPES
  sources=[];loads=[]
  with tempfile.TemporaryDirectory() as tmp:
   for i,(mesh,domain,profile) in enumerate(RECIPES):
    p=Path(tmp)/str(i);p.mkdir();(p/'cfd-artifacts.zip').write_bytes(b'fixture')
    f={'mesh_name':mesh,'domain_name':domain,'inputs':{'density_kg_m3':1,'kinematic_viscosity_m2_s':.0001,'inlet_velocity_m_s':.01,'local_refinement_profile':profile},'source':{'source_stl_sha256':'a'*64},'cells':1000,'checks':{'solver':True},'bore_verification':{'all_pass':True}}
    sources.append({'run_id':str(i),'manifest_sha256':'b'*64,'flow':f});loads.append({'pressure_force_N':[i*1e-8,0,0],'viscous_estimate_force_N':[0,-i*1e-9,0],'total_estimate_force_N':[i*1e-8,-i*1e-9,0],'total_estimate_moment_N_m':[0,0,i*1e-10],'force_normalization_N':6e-8,'checks':{'valid':True}})
   manifest={'parent_design_id':'parent','artifacts':{'cfd-artifacts.zip':'c'*64}}
   with patch('kcee.flow_forces_run.verify_directory',return_value=(manifest,'b'*64)),patch('kcee.flow_forces_run.from_archive',side_effect=loads):data=summarize(tmp,sources)
   self.assertEqual(len(data['comparisons']),5);c=data['comparisons'][0]
   self.assertEqual(c['signed_changes']['pressure_force_N'],[1e-8,0,0]);self.assertEqual(c['signed_changes']['viscous_estimate_force_N'],[0,-1e-9,0]);self.assertTrue(math.isfinite(c['total_estimate_force_change_normalized']))
   sources[-1]['flow']['inputs']['density_kg_m3']=2
   with patch('kcee.flow_forces_run.verify_directory',return_value=(manifest,'b'*64)),patch('kcee.flow_forces_run.from_archive',side_effect=loads),self.assertRaises(ValueError):summarize(tmp,sources)
 def test_registered_force_inventory_backup_and_tamper_detection(self):
  import uuid
  from kcee.flow_forces_run import save
  from kcee.provenance import verify_directory,IntegrityError
  from kcee.run_backup import export_run,restore_run
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);parent=root/str(uuid.uuid4());parent.mkdir()
   for n in ('requirements.json','geometry.json','geometry-request.json'):(parent/n).write_text('{}')
   (parent/'bracket.stl').write_text('synthetic inventory fixture')
   flow,files=fixture();load=from_archive(archive(files),flow)
   row={'run_id':str(uuid.uuid4()),'manifest_sha256':'b'*64,'archive_sha256':'c'*64,'mesh_name':'coarse','domain_name':'base','local_profile':'baseline','loads':load}
   data={'studies':[row],'benchmark':benchmark(),'comparisons':[],'checks':{'fixture':True}}
   dest=save(root,parent.name,{'manifest_sha256':'d'*64},data);m,digest=verify_directory(dest)
   self.assertEqual(m['kind'],'bracket_flow_forces');self.assertEqual(len((dest/'verification.csv').read_text().splitlines()),4)
   bundle=root/'force.zip';receipt=export_run(dest,bundle,digest);restore_parent=root/'restore';restore_parent.mkdir();restored=restore_run(bundle,restore_parent/dest.name,receipt['bundle_sha256'],digest);self.assertEqual(restored['manifest_sha256'],digest)
   (dest/'verification.csv').write_text('tampered')
   with self.assertRaises(IntegrityError):verify_directory(dest,expected_digest=digest)
 def test_native_parent_without_kind_reports_missing_sources(self):
  from unittest.mock import Mock,patch
  from kcee.flow_forces_run import run_study
  registry=Mock();registry.get.return_value={'manifest':{},'manifest_sha256':'a'*64}
  with tempfile.TemporaryDirectory() as root,patch('kcee.flow_sources.reusable',return_value=None),self.assertRaisesRegex(ValueError,'six source cases'):
   run_study(root,'native-parent',registry)
