"""Explicit pinned native llama.cpp and official model provisioning."""
import hashlib,json,os,tarfile,urllib.request
from pathlib import Path,PurePosixPath
root=Path(__file__).resolve().parents[1];local=root/'.local/ai';models=root/'models/ai';local.mkdir(parents=True,exist_ok=True);models.mkdir(parents=True,exist_ok=True)
assets=[(local/'llama-b11417.tar.gz','https://github.com/ggml-org/llama.cpp/releases/download/b11417/llama-b11417-bin-macos-arm64.tar.gz',11965040,'7ee64cdecfc7a5423db3c518fd0c880a061104555a703c8c6c5fd0a109691957'),(models/'Qwen3-4B-Q4_K_M.gguf','https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf',2497280256,'7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5')]
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()
for path,url,size,expected in assets:
    if not path.exists():
        partial=path.with_suffix(path.suffix+'.part');offset=partial.stat().st_size if partial.exists() else 0
        request=urllib.request.Request(url,headers={'Range':f'bytes={offset}-'} if offset else {})
        with urllib.request.urlopen(request,timeout=60) as response:
            if offset and (response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):offset=0
            total=offset;last=int(total/size*20)
            with partial.open('ab' if offset else 'wb') as stream:
                for block in iter(lambda:response.read(1024*1024),b''):
                    stream.write(block);total+=len(block)
                    if total>size:raise ValueError('Download exceeds pinned asset size')
                    progress=int(total/size*20)
                    if progress>last:print(path.name+': '+str(min(progress*5,100))+'%',flush=True);last=progress
        if partial.stat().st_size!=size or digest(partial)!=expected:raise ValueError('Downloaded asset differs from upstream digest')
        partial.rename(path)
    if path.stat().st_size!=size or digest(path)!=expected:raise ValueError('Pinned asset integrity mismatch')
binaries=local/'llama';binaries.mkdir(exist_ok=True)
with tarfile.open(assets[0][0]) as archive:
    for member in archive.getmembers():
        relative=PurePosixPath(member.name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe runtime archive path')
        target=binaries/str(relative)
        target.resolve().relative_to(binaries.resolve())
        if member.isdir():target.mkdir(parents=True,exist_ok=True)
        elif member.isfile():
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(member) as source,target.open('wb') as dest:
                for block in iter(lambda:source.read(1024*1024),b''):dest.write(block)
            target.chmod(member.mode&0o755)
        elif member.issym():
            link=PurePosixPath(member.linkname)
            if link.is_absolute() or '..' in link.parts:raise ValueError('Unsafe runtime link')
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() and not target.is_symlink():target.symlink_to(member.linkname)
        else:raise ValueError('Unsupported runtime archive member')
servers=list(binaries.rglob('llama-server'))
if len(servers)!=1:raise ValueError('Expected exactly one llama-server binary')
manifest={'backend':'llama.cpp Metal','release':'b11417','runtime_archive_sha256':assets[0][3],'server_relative_path':str(servers[0].relative_to(root)),'server_sha256':digest(servers[0]),'model':'Qwen/Qwen3-4B-GGUF','model_revision':'bc640142c66e1fdd12af0bd68f40445458f3869b','model_relative_path':str(assets[1][0].relative_to(root)),'model_sha256':assets[1][3],'context_tokens':8192,'output_tokens':768,'model_source_url':assets[1][1],'runtime_source_url':assets[0][1],'hash_origin':'GitHub release asset digest and official Hugging Face LFS SHA-256','runtime_files':{str(path.relative_to(root)):digest(path) for path in binaries.rglob('*') if path.is_file() and not path.is_symlink()}}
(local/'runtime-manifest.json').write_text(json.dumps(manifest,indent=2));print('Native AI runtime and official model provisioned and verified.',flush=True)
