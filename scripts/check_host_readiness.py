"""Read-only portable host/reference-run checks; no installation or model downloads."""
import argparse,hashlib,json,platform,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.provenance import verify_directory

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://localhost:8000');parser.add_argument('--reference-run');parser.add_argument('--manifest-sha256');parser.add_argument('--output',required=True);args=parser.parse_args()
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
        if not data['geometry']['picogk'] or not data['structural']['calculix']:raise ValueError('Native geometry or structural worker unavailable')
        return data
    check('geometry_structural_services',capabilities)
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
    report={'schema_version':1,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'details':details,'status':'current_geometry_fea_stack_ready' if all(checks.values()) else 'needs_attention','limitations':['This checks the current geometry/FEA stack, not full KCEE readiness','AI, voice, thermal, CFD and chemistry are not validated here','Destination performance, new native generation and new solver reproduction still require acceptance runs']}
    with Path(args.output).open('x') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report,indent=2));return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
