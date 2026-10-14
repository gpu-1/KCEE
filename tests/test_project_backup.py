import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from scripts.backup_project import unpack,PG_IMAGE,files
class BundleTests(unittest.TestCase):
 def bundle(self,root,path='source/README.md'):
  bundle=root/'backup.zip';raw=b'Project source';manifest={'schema_version':1,'postgres_image':PG_IMAGE,'files':{path:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}}}
  with zipfile.ZipFile(bundle,'w') as z:z.writestr(path,raw);z.writestr('backup-manifest.json',json.dumps(manifest))
  return bundle,hashlib.sha256(bundle.read_bytes()).hexdigest()
 def test_fresh_destination_and_external_hash(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bundle,digest=self.bundle(root);destination=root/'new'
   with self.assertRaises(ValueError):unpack(bundle,destination,'0'*64)
   self.assertFalse(destination.exists());unpack(bundle,destination,digest)
   self.assertEqual((destination/'source/README.md').read_bytes(),b'Project source')
   with self.assertRaises(ValueError):unpack(bundle,destination,digest)
 def test_traversal_is_rejected_before_extraction(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bundle,digest=self.bundle(root,'source/../../outside')
   with self.assertRaises(ValueError):unpack(bundle,root/'new',digest)
   self.assertFalse((root/'new').exists())
 def test_internal_corruption_removes_partial_destination(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bundle,digest=self.bundle(root)
   with zipfile.ZipFile(bundle) as z:manifest=json.loads(z.read('backup-manifest.json'))
   manifest['files']['source/README.md']['sha256']='0'*64
   with zipfile.ZipFile(bundle,'w') as z:z.writestr('source/README.md',b'Project source');z.writestr('backup-manifest.json',json.dumps(manifest))
   with self.assertRaises(ValueError):unpack(bundle,root/'new',hashlib.sha256(bundle.read_bytes()).hexdigest())
   self.assertFalse((root/'new').exists())

class SnapshotInventoryTests(unittest.TestCase):
 def test_restored_snapshot_excludes_credentials_and_native_environments(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name in ('scripts/tool.py','host/macos/ai/.venv/module.py','.env','.local/server.key','models/weights.bin'):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('test')
   inventory=files(root)
   self.assertIn('source/scripts/tool.py',inventory)
   self.assertFalse(any(name.endswith(('.env','server.key','weights.bin','module.py')) for name in inventory))
