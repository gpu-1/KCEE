"""Explicitly provision local Kokoro weights and an isolated native Python runtime."""
import argparse,hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--python',required=True,help='Python 3.10–3.13 executable');args=parser.parse_args()
root=Path(__file__).resolve().parents[1];local=root/'.local/kokoro';models=root/'models/kokoro';local.mkdir(parents=True,exist_ok=True);models.mkdir(parents=True,exist_ok=True)
version=json.loads(subprocess.check_output([args.python,'-c','import sys,json;print(json.dumps(list(sys.version_info[:2])))'],text=True))
if not ((3,10)<=tuple(version)<(3,14)):raise SystemExit('Kokoro requires Python 3.10–3.13')
venv=local/'venv'
if not (venv/'bin/python').exists():subprocess.run([args.python,'-m','venv',str(venv)],check=True)
python=venv/'bin/python';subprocess.run([str(python),'-m','pip','install','-r',str(root/'host/macos/kokoro/requirements.lock')],check=True)
files={}
previous=json.loads((models/'runtime-manifest.json').read_text()) if (models/'runtime-manifest.json').exists() else None
for name,size in (('kokoro-v1.0.int8.onnx',92361271),('voices-v1.0.bin',28214398)):
    url='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'+name;path=models/name
    if not path.exists():
        temporary=path.with_suffix(path.suffix+'.download')
        with urllib.request.urlopen(url,timeout=60) as response,temporary.open('xb') as stream:
            for chunk in iter(lambda:response.read(1024*1024),b''):stream.write(chunk)
        if temporary.stat().st_size!=size:raise ValueError('Model asset size mismatch')
        temporary.rename(path)
    if path.stat().st_size!=size:raise ValueError('Existing model file size mismatch')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if previous is not None and previous['files'][name]['sha256']!=digest:raise ValueError('Existing model differs from its recorded hash; inspect before reprovisioning')
    files[name]={'sha256':digest,'size_bytes':size,'source_url':url}
manifest={'backend':'kokoro-onnx','package_version':'0.6.1','model_release':'model-files-v1.0','precision':'int8','files':files,'model_license':'Apache-2.0','runtime_license':'MIT','hash_origin':'Locally computed after explicit download from upstream release; release supplied no digest'}
(models/'runtime-manifest.json').write_text(json.dumps(manifest,indent=2))
(local/'requirements.freeze.txt').write_text(subprocess.check_output([str(python),'-m','pip','freeze'],text=True))
print('Local Kokoro runtime and weights provisioned; no runtime model downloads are needed.')
