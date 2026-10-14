"""Read-only integrity checks for explicitly provisioned Kokoro model files."""
import hashlib,json,re
from pathlib import Path

def verify_voice_models(directory):
    directory=Path(directory);raw=(directory/'runtime-manifest.json').read_bytes();manifest=json.loads(raw)
    expected={'kokoro-v1.0.int8.onnx','voices-v1.0.bin'}
    if set(manifest['files'])!=expected:raise ValueError('Incomplete Kokoro model manifest')
    files={}
    for name in sorted(expected):
        metadata=manifest['files'][name];path=directory/name
        if path.is_symlink() or not path.is_file():raise ValueError('Missing or unsafe Kokoro model file')
        if not re.fullmatch('[a-f0-9]{64}',metadata['sha256']):raise ValueError('Invalid recorded model digest')
        if path.stat().st_size!=metadata['size_bytes']:raise ValueError('Kokoro model size mismatch')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        if digest.hexdigest()!=metadata['sha256']:raise ValueError('Kokoro model hash mismatch')
        files[name]={'sha256':digest.hexdigest(),'size_bytes':metadata['size_bytes']}
    return {'model_manifest_sha256':hashlib.sha256(raw).hexdigest(),'files':files,'hash_origin':manifest.get('hash_origin','Not recorded')}
