"""Portable verified single-run bundles. Restore only into a new destination."""
import hashlib,json,os,tempfile,zipfile
from pathlib import Path
from kcee.provenance import IntegrityError,verify_directory

def export_run(directory,output,expected_digest):
    directory=Path(directory);output=Path(output)
    manifest,digest=verify_directory(directory,expected_digest=expected_digest)
    # Exclusive output creation prevents accidental replacement of an existing backup.
    with output.open('xb') as stream:
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(directory.iterdir()):archive.writestr(path.name,path.read_bytes())
    return {'run_id':manifest['run_id'],'manifest_sha256':digest,'bundle_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}

def restore_run(bundle,destination,expected_bundle_digest,expected_manifest_digest):
    bundle=Path(bundle);destination=Path(destination)
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=expected_bundle_digest:raise IntegrityError('Backup bundle hash mismatch')
    if destination.exists() or destination.is_symlink():raise IntegrityError('Restore destination must not exist')
    with zipfile.ZipFile(bundle) as archive:
        entries=archive.infolist();names=[entry.filename for entry in entries]
        if len(names)!=len(set(names)) or any('/' in n or '\\' in n or n in ('.','..') for n in names):raise IntegrityError('Unsafe backup paths')
        if sum(e.file_size for e in entries)>512*1024*1024:raise IntegrityError('Backup exceeds restore size limit')
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            stage=Path(temporary)/destination.name;stage.mkdir()
            for entry in entries:(stage/entry.filename).write_bytes(archive.read(entry))
            manifest,digest=verify_directory(stage,expected_digest=expected_manifest_digest)
            # Never merge files into an existing saved run.
            destination.mkdir()
            try:
                for path in stage.iterdir():os.rename(path,destination/path.name)
            except Exception:
                raise IntegrityError('Restore incomplete; inspect the new destination before retrying')
    return {'run_id':manifest['run_id'],'manifest_sha256':digest,'registration':'not_registered'}
