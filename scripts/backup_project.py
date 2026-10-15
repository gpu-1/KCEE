"""Verified project bundle and fresh, isolated database restore. Never overwrites data."""
import argparse,hashlib,json,os,re,secrets,shutil,stat,subprocess,sys,tempfile,time,uuid,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
PG_IMAGE='pgvector/pgvector:0.8.6-pg18-trixie@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def compose(root,*args,**options):
    marker=Path(root)/'.local/restore-project.json';prefix=[]
    if marker.is_file():
        project=json.loads(marker.read_text())['project']
        if not re.fullmatch('kcee-restored-[a-f0-9]{12}',project):raise ValueError('Invalid isolated restore project')
        prefix=['-p',project]
    return subprocess.run(['docker','compose',*prefix,*args],cwd=root,check=True,**options)

def audit(root):
    compose(root,'build','api',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    result=compose(root,'run','--rm','--no-deps','-T','-e','PYTHONPATH=/app','-v',str(root/'scripts')+':/audit:ro','api','python','/audit/verify_restored_data.py',capture_output=True,text=True)
    report=json.loads(result.stdout)
    report['counts']['knowledge_chunks']=int(compose(root,'exec','-T','postgres','psql','-U','kcee','-d','kcee','-At','-c','SELECT count(*) FROM knowledge_chunks',capture_output=True,text=True).stdout.strip())
    return report
def verify_restore_inventory(expected,actual):
    if actual['counts']!=expected['counts']:raise ValueError('Restored database inventory differs')
    if expected.get('library_snapshot') and actual.get('library_snapshot')!=expected['library_snapshot']:raise ValueError('Restored library metadata differs from backup')
    if 'document_page_notes' in expected['counts'] or expected.get('review_notes') is not None:
        if not expected.get('review_notes') or expected['review_notes'].get('integrity')!='verified' or actual.get('review_notes')!=expected['review_notes']:raise ValueError('Restored review note history differs from backup verification')

def files(root):
    result={}
    for prefix,target in (('runs','runs'),('.local/studies','studies')):
        source=root/prefix
        if source.exists():
            for p in source.rglob('*'):
                if p.is_symlink():raise ValueError('Symlinks cannot be backed up')
                if p.is_file():result[target+'/'+p.relative_to(source).as_posix()]=p
    allowed_folders={'kcee','scripts','services','viewer','infra','docs','host','examples','materials','tests','.github'}
    try:
        tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root,stderr=subprocess.DEVNULL).decode().split('\0'))
        names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root,stderr=subprocess.DEVNULL).decode().split('\0')
    except (subprocess.CalledProcessError,FileNotFoundError):
        top={'README.md','LICENSE','.gitignore','.env.example','compose.yaml','compose.test.yaml','pyproject.toml','requirements.txt','.dockerignore','.gitattributes','.python-version','.editorconfig','requirements.lock'}
        names=[p.relative_to(root).as_posix() for folder in allowed_folders for p in (root/folder).rglob('*') if p.is_file() and not any(part in ('__pycache__','.venv','.pytest_cache','node_modules','dist','bin','obj') for part in p.relative_to(root).parts)]
        names.extend(name for name in top if (root/name).is_file());tracked=set(names)
    for relative in ('.local/runtime-manifest.json','.local/ai/runtime-manifest.json','.local/embedding-runtime/model-manifest.json'):
        path=root/relative
        if path.is_file() and not path.is_symlink():result['runtime-manifests/'+relative[7:].replace('/','-')]=path
    allowed={'kcee','scripts','services','viewer','infra','docs','host','examples','materials','tests','.github'}
    for name in names:
        if not name:continue
        path=root/name
        if name.startswith(('.local/','models/','runs/','.git/')) or (name.startswith('.env') and name!='.env.example'):continue
        if len(PurePosixPath(name).parts)==1 and name not in tracked:continue
        if len(PurePosixPath(name).parts)>1 and PurePosixPath(name).parts[0] not in allowed:continue
        if path.is_symlink():raise ValueError('Source symlinks are not supported')
        if path.is_file():result['source/'+name]=path
    return result

def revision(root):
    try:return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError,FileNotFoundError):
        marker=root/'.local/restore-project.json'
        return json.loads(marker.read_text()).get('git_commit','restored-source-snapshot') if marker.is_file() else 'unversioned-source-snapshot'

def export(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or not output.parent.is_dir():raise ValueError('Choose a new bundle path with an existing parent directory')
    for folder in ('geometry','assistant','voice','embeddings','control'):
        queue=root/'.local'/folder/'queue'
        if list(queue.glob('*.processing.json')) or list(queue.glob('*.request.json')):raise ValueError('Finish or clear pending worker jobs before backup')
    running=compose(root,'ps','--status','running','--services',capture_output=True,text=True).stdout.split()
    paused='api' in running
    try:
        if paused:
            active=compose(root,'exec','-T','api','python','-c',"import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000/knowledge/import-state'))))",capture_output=True,text=True)
            if json.loads(active.stdout)['active']:raise ValueError('Finish or cancel the active document import before backup')
        if paused:compose(root,'stop','--timeout','150','api',stdout=subprocess.DEVNULL)
        with tempfile.TemporaryDirectory(prefix='kcee-backup-') as tmp:
            database=Path(tmp)/'database.dump'
            with database.open('wb') as stream:compose(root,'exec','-T','postgres','pg_dump','-U','kcee','-d','kcee','-Fc','--no-owner',stdout=stream)
            report=audit(root);inventory=files(root);inventory['database.dump']=database
            manifest={'schema_version':1,'created_at':time.time(),'git_commit':revision(root),'postgres_image':PG_IMAGE,'verification':report,'files':{name:{'sha256':digest(path),'bytes':path.stat().st_size} for name,path in inventory.items()},'excluded':['credentials and signing keys','model weights and native binaries','transient queues and generated speech']}
            staging=output.with_name(output.name+'.partial-'+uuid.uuid4().hex)
            try:
                with staging.open('xb') as stream:
                    os.chmod(staging,0o600)
                    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
                        for name,path in inventory.items():archive.write(path,name)
                        archive.writestr('backup-manifest.json',json.dumps(manifest,sort_keys=True,indent=2))
                for name,path in inventory.items():
                    if digest(path)!=manifest['files'][name]['sha256']:raise ValueError('Files changed during backup; retry after stopping writers')
                staging.rename(output)
            finally:
                if staging.exists():staging.unlink()
        receipt={'created_at':time.time(),'bundle':str(output),'bundle_sha256':digest(output),'counts':report['counts'],'review_notes':report.get('review_notes'),'library_snapshot':report.get('library_snapshot')}
        receipt_path=output.with_suffix(output.suffix+'.receipt.json');receipt_path.write_text(json.dumps(receipt,indent=2));os.chmod(receipt_path,0o600)
        return receipt
    finally:
        if paused:compose(root,'start','api',stdout=subprocess.DEVNULL)

def unpack(bundle,destination,expected):
    bundle=Path(bundle);destination=Path(destination)
    if destination.exists() or not destination.parent.is_dir():raise ValueError('Restore requires a new destination directory')
    if digest(bundle)!=expected:raise ValueError('Bundle differs from externally trusted SHA-256')
    with zipfile.ZipFile(bundle) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or len(names)>100000:raise ValueError('Invalid bundle inventory')
        manifest=json.loads(archive.read('backup-manifest.json'))
        if manifest.get('schema_version')!=1 or manifest.get('postgres_image')!=PG_IMAGE or set(names)!=set(manifest['files'])|{'backup-manifest.json'}:raise ValueError('Unsupported or incomplete bundle')
        if sum(info.file_size for info in archive.infolist())>50*1024**3:raise ValueError('Bundle exceeds restore size limit')
        for info in archive.infolist():
            path=PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr>>16) or info.is_dir():raise ValueError('Unsafe archive path')
            if info.filename!='backup-manifest.json' and not (info.filename=='database.dump' or path.parts[0] in ('source','runs','studies','runtime-manifests')):raise ValueError('Unexpected bundle path')
        destination.mkdir(mode=0o700)
        try:
            for name,spec in manifest['files'].items():
                target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(name) as inp,target.open('xb') as out:shutil.copyfileobj(inp,out,1024*1024)
                os.chmod(target,stat.S_IMODE(archive.getinfo(name).external_attr>>16)&0o777 or 0o600)
                if target.stat().st_size!=spec['bytes'] or digest(target)!=spec['sha256']:raise ValueError('Bundle file integrity mismatch')
        except Exception:
            shutil.rmtree(destination);raise
    return manifest

def restore(bundle,destination,expected):
    destination=Path(destination).resolve();manifest=unpack(bundle,destination,expected)
    root=destination/'source';(root/'runs').mkdir(exist_ok=True)
    for p in (destination/'runs').iterdir():shutil.move(str(p),str(root/'runs'/p.name))
    (root/'.local').mkdir(exist_ok=True)
    for folder in ('geometry','control','voice','assistant','embeddings','studies'):(root/'.local'/folder).mkdir(mode=0o700,exist_ok=True)
    if (destination/'studies').exists():shutil.move(str(destination/'studies'),str(root/'.local/studies'))
    project='kcee-restored-'+uuid.uuid4().hex[:12]
    envfile=root/'.env';envfile.write_text('COMPOSE_PROJECT_NAME='+project+'\nPOSTGRES_PASSWORD='+secrets.token_hex(32)+'\nKCEE_APP_DB_PASSWORD='+secrets.token_hex(32)+'\n');os.chmod(envfile,0o600)
    (root/'.local/restore-project.json').write_text(json.dumps({'project':project,'git_commit':manifest.get('git_commit')}))
    if compose(root,'ps','-aq',capture_output=True,text=True).stdout.strip():raise ValueError('Fresh restore project already has containers')
    existing=subprocess.check_output(['docker','volume','ls','-q','--filter','label=com.docker.compose.project='+project],text=True).strip()
    if existing:raise ValueError('Fresh restore project already has a volume')
    (destination/'restore-report.json').write_text(json.dumps({'project':project,'root':str(root),'status':'restore_started'}))
    compose(root,'up','-d','--wait','postgres',stdout=subprocess.DEVNULL)
    with (destination/'database.dump').open('rb') as stream:compose(root,'exec','-T','postgres','pg_restore','-U','kcee','-d','kcee','--clean','--if-exists','--no-owner','--exit-on-error','--single-transaction',stdin=stream,stdout=subprocess.DEVNULL)
    report=audit(root)
    verify_restore_inventory(manifest['verification'],report)
    result={'completed_at':time.time(),'project':project,'root':str(root),'verification':report,'services_started':['postgres'],'native_setup_required':True}
    (destination/'restore-report.json').write_text(json.dumps(result,indent=2))
    status_dir=ROOT/'.local/backups';status_dir.mkdir(parents=True,exist_ok=True)
    status_file=status_dir/(project+'-restore-verification.json');status_file.write_text(json.dumps(result,indent=2));os.chmod(status_file,0o600)
    return result

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('create');create.add_argument('output')
    target=sub.add_parser('restore');target.add_argument('bundle');target.add_argument('destination');target.add_argument('--bundle-sha256',required=True)
    args=parser.parse_args();print(json.dumps(export(ROOT,args.output) if args.command=='create' else restore(args.bundle,args.destination,args.bundle_sha256),indent=2))
if __name__=='__main__':main()
