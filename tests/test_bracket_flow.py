import unittest,struct,hashlib,tempfile,re
from pathlib import Path
from kcee.bracket_flow import prepare_surface,make_case,boundary_flux,cell_positions
class BracketFlowTests(unittest.TestCase):
 def surface(self):
  vertices=[(0,0,0),(60,0,0),(60,30,0),(0,30,0),(0,0,40),(60,0,40),(60,30,40),(0,30,40)];faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
  return b'fixture'.ljust(80,b' ')+struct.pack('<I',12)+b''.join(struct.pack('<12fH',0,0,0,*vertices[a],*vertices[b],*vertices[c],0) for a,b,c in faces)
 def test_surface_conversion_keeps_source_identity_and_mm_to_m(self):
  raw=self.surface();converted,meta=prepare_surface(raw);self.assertIn(b'vertex 0.06 0.03 0.04',converted);self.assertEqual(meta['source_stl_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(meta['converted_surface_sha256'],hashlib.sha256(converted).hexdigest());self.assertEqual(meta['triangles'],12)
  for bad in [b'bad',raw[:-1],raw[:84]+raw[84:].replace(struct.pack('<f',60),struct.pack('<f',float('nan')),1)]:
   with self.assertRaises(ValueError):prepare_surface(bad)
 def test_openfoam_volume_number_with_sentence_punctuation(self):
  from kcee.bracket_flow import mesh_total_volume
  self.assertAlmostEqual(mesh_total_volume('Total volume = 0.018134128768178.  Cell volumes OK.'),.018134128768178)
  self.assertAlmostEqual(mesh_total_volume('Total volume = 1.8e-2.'),.018)
  for text in ('Total volume = nan','Total volume = -1.','Total volume = 0.','missing'):
   with self.assertRaises(ValueError):mesh_total_volume(text)
 def test_fixed_boundary_and_mesh_configuration(self):
  with tempfile.TemporaryDirectory() as tmp:
   make_case(tmp,self.surface());root=Path(tmp);self.assertIn('level (3 3)',(root/'system/snappyHexMeshDict').read_text());self.assertIn('bore4 {type searchableSphere;centre (0.00175 0.015 0.030);radius 0.005;}',(root/'system/snappyHexMeshDict').read_text());self.assertIn('nSmoothPatch 5',(root/'system/snappyHexMeshDict').read_text());self.assertIn('nSmoothScale 8',(root/'system/snappyHexMeshDict').read_text());self.assertIn('endTime 1500',(root/'system/controlDict').read_text());self.assertIn('addLayers false',(root/'system/snappyHexMeshDict').read_text());self.assertIn('simulationType laminar',(root/'constant/turbulenceProperties').read_text());self.assertIn('sides {type slip;}',(root/'0/U').read_text());self.assertIn('outlet {type fixedValue;value uniform 0;}',(root/'0/p').read_text())
 def test_signed_boundary_flow_sum_and_bad_field_rejection(self):
  self.assertAlmostEqual(boundary_flux('inlet {type calculated;value nonuniform List<scalar> 3 (-1 -2 -3);}','inlet'),-6)
  self.assertEqual(boundary_flux('bracket {type calculated;value uniform 0;}','bracket'),0)
  for value in ['inlet {value uniform 1;}','inlet {value nonuniform List<scalar> 2 (1);}','inlet {value nonuniform List<scalar> 1 (nan);}']:
   with self.assertRaises(ValueError):boundary_flux(value,'inlet')
 def test_mesh_vertex_positions_preserve_cell_addressing(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'points').write_text('FoamFile {}\n4\n((0 0 0)(1 0 0)(0 1 0)(0 0 1))');(root/'faces').write_text('FoamFile {}\n4\n(3(0 2 1)3(0 1 3)3(1 2 3)3(2 0 3))');(root/'owner').write_text('FoamFile {}\n4\n(0 0 0 0)');(root/'neighbour').write_text('FoamFile {}\n0\n()');self.assertEqual(cell_positions(root,1),[(.25,.25,.25)])
 def test_raw_archive_rejects_changed_surface_and_unsafe_paths(self):
  import io,json,zipfile,base64
  from kcee.bracket_flow_run import verified_archive
  def payload(data):return {'archive_base64':base64.b64encode(data).decode(),'archive_sha256':hashlib.sha256(data).hexdigest()}
  runtime={'package':'1912.200626-3+b1','binaries_sha256':{k:'a'*64 for k in ('snappyHexMesh','simpleFoam','checkMesh','surfaceCheck')}}
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);raw=self.surface();make_case(root,raw);buffer=io.BytesIO()
   with zipfile.ZipFile(buffer,'w') as z:
    z.writestr('runtime.json',json.dumps(runtime))
    for p in root.rglob('*'):
     if p.is_file():z.writestr(p.relative_to(root).as_posix(),b'changed' if p.name=='bracket.stl' else p.read_bytes())
   with self.assertRaisesRegex(ValueError,'surface differs'):verified_archive(payload(buffer.getvalue()),raw)
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w') as z:z.writestr('../escape','x')
  with self.assertRaisesRegex(ValueError,'Unsafe flow archive'):verified_archive(payload(buffer.getvalue()),self.surface())
 def test_failed_worker_retains_readable_diagnostic_archive(self):
  from unittest.mock import patch
  from kcee.bracket_flow import run_payload
  import io,zipfile,base64
  with patch('kcee.bracket_flow.command',side_effect=ValueError('meshing fixture failure')),patch('kcee.bracket_flow.subprocess.check_output',return_value='1912.200626-3+b1'),patch('shutil.which',return_value=__file__):payload=run_payload(self.surface())
  self.assertIsNone(payload['result']);self.assertIn('meshing fixture failure',payload['error'])
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(payload['archive_base64']))) as z:self.assertIn('meshing fixture failure',z.read('job.log').decode());self.assertIn('constant/triSurface/bracket.stl',z.namelist())
