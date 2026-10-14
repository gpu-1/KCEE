import hashlib,json,tempfile,unittest
from pathlib import Path
from kcee.ai_runtime import verify_ai_runtime
class AIRuntimeTests(unittest.TestCase):
    def test_runtime_and_model_tamper_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);server=root/'.local/ai/llama/llama-server';model=root/'models/ai/model.gguf';server.parent.mkdir(parents=True);model.parent.mkdir(parents=True);server.write_bytes(b'binary');model.write_bytes(b'model')
            digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            manifest={'server_relative_path':str(server.relative_to(root)),'server_sha256':digest(server),'model_relative_path':str(model.relative_to(root)),'model_sha256':digest(model),'model':'official-model','model_revision':'pinned','runtime_files':{str(server.relative_to(root)):digest(server)}}
            path=root/'.local/ai/runtime-manifest.json';path.write_text(json.dumps(manifest))
            self.assertEqual(verify_ai_runtime(root)['runtime_files_checked'],1)
            model.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify_ai_runtime(root)
            model.write_bytes(b'model');server.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify_ai_runtime(root)
