"""Build/test in a disposable project; never touches the normal KCEE volume."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile

parser=argparse.ArgumentParser();parser.add_argument("--viewer",action="store_true");parser.add_argument("--fea",action="store_true");args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='kcee-check-') as tmp:
    checkout=Path(tmp)/'project'
    shutil.copytree(root,checkout,ignore=shutil.ignore_patterns('.git','.env','.local','.venv','__pycache__','node_modules','runs','models'))
    (checkout/'runs').mkdir()
    (checkout/'.local/embeddings').mkdir(parents=True,exist_ok=True)
    (checkout/'.local/assistant').mkdir(parents=True,exist_ok=True)
    (checkout/'.local/voice').mkdir(parents=True,exist_ok=True)
    (checkout/'.local/studies').mkdir(parents=True,exist_ok=True)
    (checkout/'.local/control').mkdir(parents=True,exist_ok=True)
    (checkout/'.local/geometry').mkdir(parents=True)
    environment={**os.environ,'KCEE_TEST_UID':str(os.getuid()),'KCEE_TEST_GID':str(os.getgid()),'POSTGRES_PASSWORD':secrets.token_hex(24),'KCEE_APP_DB_PASSWORD':secrets.token_hex(24)}
    command=['docker','compose','-p','kcee-check-'+secrets.token_hex(6),'-f','compose.yaml','-f','compose.test.yaml']
    if args.viewer:
        environment['KCEE_TEST_VIEWER_URL']='http://viewer:5173'
        command+=['--profile','viewer']
    if args.fea:
        environment['KCEE_TEST_FEA']='1'
        command+=['--profile','fea']
    try:
        subprocess.run(command+['config','--quiet'],cwd=checkout,env=environment,check=True)
        if args.viewer:
            subprocess.run(command+['up','--build','-d','--wait','viewer'],cwd=checkout,env=environment,check=True)
        if args.fea:
            subprocess.run(command+['up','--build','-d','--wait','structural','thermal','cfd'],cwd=checkout,env=environment,check=True)
        subprocess.run(command+['run','--rm','--build','test'],cwd=checkout,env=environment,check=True)
    finally:
        subprocess.run(command+['down','-v','--remove-orphans'],cwd=checkout,env=environment,check=True)
