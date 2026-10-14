"""Read-only portable host/reference-run checks; no installation or model downloads."""
import argparse,hashlib,json,platform,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.provenance import verify_directory

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://localhost:8000');parser.add_argument('--reference-run');parser.add_argument('--manifest-sha256');parser.add_argument('--output',required=True);parser.add_argument('--voice',action='store_true',help='Also check native Kokoro worker, dependencies and model hashes');parser.add_argument('--ai',action='store_true',help='Also check the native model/runtime hashes and AI gateway');args=parser.parse_args()
    if bool(args.reference_run)!=bool(args.manifest_sha256):parser.error('Reference run and trusted manifest hash must be supplied together')
    root=Path(__file__).resolve().parents[1];checks={};details={}
    def check(name,operation):
        try:details[name]=operation();checks[name]=True
        except Exception as error:details[name]={'error':str(error)};checks[name]=False
    def command(argv):return subprocess.check_output(argv,cwd=root,stderr=subprocess.PIPE,text=True,timeout=15).strip()
    def api(path):
        with urlopen(args.base_url+path,timeout=15) as response:return json.load(response)
    checks['apple_silicon_macos']=platform.system()=='Darwin' and platform.machine()=='arm64'
    details['host']={'system':platform.system(),'architecture':platform.machine(),'python':platform.python_version()}
    check('docker_engine',lambda:command(['docker','info','--format','{{.Architecture}}']))
    check('compose',lambda:command(['docker','compose','version','--short']))
    check('native_dotnet',lambda:command([str(root/'.local/dotnet/dotnet'),'--version']))
    def native():
        path=root/'.local/picogk/Kcee.Geometry'
        if not path.is_file():raise ValueError('PicoGK adapter not provisioned')
        return {'adapter_binary_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    check('picogk_adapter_present',native)
    def ready():
        data=api('/ready')
        if data.get('status')!='ready':raise ValueError('API/database not ready')
        return data
    check('api_database',ready)
    def capabilities():
        data=api('/capabilities')
        if not data['geometry']['picogk'] or not data['structural']['calculix'] or not data.get('thermal',{}).get('steady_1d'):raise ValueError('Native geometry, structural or thermal worker unavailable')
        return data
    check('geometry_structural_services',capabilities)
    if args.ai:
        from kcee.ai_runtime import verify_ai_runtime
        check('native_ai_integrity',lambda:verify_ai_runtime(root))
        def ai_worker():
            data=api('/assistant/status');manifest=json.loads((root/'.local/ai/runtime-manifest.json').read_text())
            if not data.get('available') or data.get('model_sha256')!=manifest['model_sha256']:raise ValueError('Local AI gateway/model identity unavailable')
            return data
        check('native_ai_worker',ai_worker)
    if args.voice:
        from kcee.voice_runtime import verify_voice_models
        check('kokoro_model_integrity',lambda:verify_voice_models(root/'models/kokoro'))
        def voice_runtime():
            expected=dict(line.split('==',1) for line in (root/'host/macos/kokoro/requirements.lock').read_text().splitlines() if line)
            script='import importlib.metadata,json,sys;expected=json.loads(sys.argv[1]);print(json.dumps({name:importlib.metadata.version(name) for name in expected}))'
            actual=json.loads(command([str(root/'.local/kokoro/venv/bin/python'),'-c',script,json.dumps(expected)]))
            if actual!=expected:raise ValueError('Native Kokoro dependency versions differ from pinned lock')
            return {'python':command([str(root/'.local/kokoro/venv/bin/python'),'--version']),'dependencies':actual}
        check('kokoro_runtime_dependencies',voice_runtime)
        def voice_worker():
            data=api('/voice/status')
            if not data.get('available') or data.get('backend')!='native_kokoro':raise ValueError('Native Kokoro worker unavailable')
            return data
        check('kokoro_worker',voice_worker)
    if args.reference_run:
        from uuid import UUID
        run_id=str(UUID(args.reference_run))
        def reference():
            manifest,digest=verify_directory(root/'runs'/run_id,expected_digest=args.manifest_sha256)
            record=api('/runs/'+run_id)
            if record['manifest_sha256']!=digest or record['manifest']!=manifest:raise ValueError('Local/reference database mismatch')
            if api('/runs/'+run_id+'/verify')['integrity']!='verified':raise ValueError('Reference verification failed')
            return {'run_id':run_id,'manifest_sha256':digest,'validation_status':record['validation_status']}
        check('saved_reference_run',reference)
    report={'schema_version':1,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'details':details,'status':('current_geometry_fea'+('_ai' if args.ai else '')+('_voice' if args.voice else '')+'_stack_ready') if all(checks.values()) else 'needs_attention','limitations':['This checks the current geometry/FEA'+('/AI' if args.ai else '')+('/voice' if args.voice else '')+' stack, not full KCEE readiness','Thermal, CFD, chemistry and speech input are not validated here','Destination performance, new native generation, solver reproduction and audible voice quality still require acceptance runs',*(['AI checks are preflight only; explanation quality is not certified'] if args.ai else ['AI is not checked; add --ai to include its preflight']),*(['Voice checks are read-only preflight; no synthesis or playback is performed'] if args.voice else ['Voice is not included; add --voice to check its preflight'])]}
    with Path(args.output).open('x') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report,indent=2));return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
