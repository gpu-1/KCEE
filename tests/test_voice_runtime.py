import hashlib,json,tempfile,unittest
from pathlib import Path
from kcee.voice_runtime import verify_voice_models
class VoiceRuntimeTests(unittest.TestCase):
    def test_models_match_recorded_hashes_and_detect_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);files={}
            for name in ('kokoro-v1.0.int8.onnx','voices-v1.0.bin'):
                raw=name.encode();(root/name).write_bytes(raw);files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
            manifest=root/'runtime-manifest.json';manifest.write_text(json.dumps({'files':files}))
            self.assertEqual(verify_voice_models(root)['files'],files)
            path=root/'voices-v1.0.bin';path.write_bytes(b'x'*files[path.name]['size_bytes'])
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify_voice_models(root)
            path.unlink()
            with self.assertRaisesRegex(ValueError,'Missing'):verify_voice_models(root)
            manifest.write_text(json.dumps({'files':{}}))
            with self.assertRaisesRegex(ValueError,'Incomplete'):verify_voice_models(root)
