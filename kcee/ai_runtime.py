"""Read-only hashes for the provisioned native model and runtime files."""
import hashlib,json,re
from pathlib import Path

def verify_ai_runtime(root):
    root=Path(root);raw=(root/'.local/ai/runtime-manifest.json').read_bytes();manifest=json.loads(raw)
    def checked(relative,expected,base):
        path=root/relative
        try:path.resolve().relative_to((root/base).resolve())
        except ValueError:raise ValueError('AI runtime path escapes its project directory')
        if path.is_symlink() or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Invalid AI runtime file identity')
        value=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
        if value.hexdigest()!=expected:raise ValueError('Native AI file hash mismatch')
    files=manifest['runtime_files']
    if not files or files.get(manifest['server_relative_path'])!=manifest['server_sha256']:raise ValueError('Incomplete native AI runtime manifest')
    for relative,expected in files.items():checked(relative,expected,'.local/ai/llama')
    checked(manifest['model_relative_path'],manifest['model_sha256'],'models/ai')
    return {'runtime_manifest_sha256':hashlib.sha256(raw).hexdigest(),'model':manifest['model'],'model_revision':manifest['model_revision'],'model_sha256':manifest['model_sha256'],'server_sha256':manifest['server_sha256'],'runtime_files_checked':len(files)}
