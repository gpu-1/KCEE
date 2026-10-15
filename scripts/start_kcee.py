"""Start the provisioned local geometry/FEA stack and save a readiness report."""
import argparse,subprocess,sys
from pathlib import Path
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true',help='Rebuild container images before startup')
    parser.add_argument('--voice',action='store_true',help='Start the already provisioned local Kokoro worker')
    parser.add_argument('--ai',action='store_true',help='Start already provisioned native local study AI')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    for path,message in ((root/'.env','Configure .env first; see docs/operations/install-macos.md'),(root/'.local/picogk/Kcee.Geometry','Provision native PicoGK first; see host/macos/picogk/README.md')):
        if not path.is_file():raise SystemExit(message)
    try:
        subprocess.run(['docker','info','--format','{{.Architecture}}'],cwd=root,check=True,stdout=subprocess.DEVNULL,timeout=20)
        subprocess.run([sys.executable,str(root/'scripts/start_geometry_worker.py')],cwd=root,check=True,timeout=30)
        subprocess.run([sys.executable,str(root/'scripts/start_service_supervisor.py')],cwd=root,check=True,timeout=30)
        (root/'.local/embeddings').mkdir(parents=True,exist_ok=True)
        (root/'.local/assistant').mkdir(parents=True,exist_ok=True)
        if args.ai:subprocess.run([sys.executable,str(root/'scripts/start_ai_worker.py')],cwd=root,check=True,timeout=150)
        (root/'.local/voice').mkdir(parents=True,exist_ok=True)
        if args.voice:subprocess.run([sys.executable,str(root/'scripts/start_voice_worker.py')],cwd=root,check=True,timeout=30)
        (root/'.local/studies').mkdir(parents=True,exist_ok=True)
        command=['docker','compose','--profile','viewer','--profile','fea','up','-d','--wait','--wait-timeout','120']
        if args.build:command.append('--build')
        subprocess.run(command,cwd=root,check=True)
        reports=root/'.local/readiness';reports.mkdir(parents=True,exist_ok=True)
        report=reports/('startup-'+str(uuid4())+'.json')
        readiness=[sys.executable,str(root/'scripts/check_host_readiness.py'),'--output',str(report)]
        if args.voice:readiness.append('--voice')
        if args.ai:readiness.append('--ai')
        result=subprocess.run(readiness,cwd=root)
        print('Readiness report: '+str(report),flush=True)
        if result.returncode:return result.returncode
        print('KCEE geometry/FEA/CFD'+('/AI' if args.ai else '')+('/voice' if args.voice else '')+' stack ready. Open http://localhost:5173/',flush=True)
        return 0
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
        print('Startup did not complete: '+str(error),file=sys.stderr)
        print('Services already started are retained. Correct the reported issue and run this command again.',file=sys.stderr)
        return 1
    except FileNotFoundError:
        print('Docker is unavailable. Install/start Docker Desktop before retrying.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
