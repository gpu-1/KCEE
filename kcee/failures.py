"""Read-only discovery of retained failures, separate from verified saved runs."""
import json,zipfile
from pathlib import Path
from uuid import UUID

def failure_reason(archive):
    if archive.is_symlink() or not archive.is_file():return 'Service or generation failure; inspect the failure record.'
    try:
        with zipfile.ZipFile(archive) as zipped:
            entry=zipped.getinfo('job.log')
            if entry.file_size>128*1024:return 'Diagnostics retained; log exceeds preview limit.'
            log=zipped.read(entry).decode('utf-8',errors='replace')
        reason=next((line.strip() for line in reversed(log.splitlines()) if line.strip()),'')
        for pattern,message in [('Wrong topology of boundary mesh','Surface parameterization failed.'),('overlapping facets','Volume meshing rejected overlapping boundary facets.'),('Free-end load patch not resolved','The mesh did not resolve the load strip.'),('Mesh exceeds demo node budget','The mesh exceeded the demonstrator node limit.'),('TimeoutExpired','The meshing or solver time limit was exceeded.'),('Bracket solve failed','The structural solver failed.')]:
            if pattern in reason:return message
        return 'Meshing or solver failure; inspect the retained diagnostics.'
    except (OSError,KeyError,ValueError,zipfile.BadZipFile):return 'Diagnostic archive unavailable or unreadable.'

def list_failures(root,limit=50):
    records=[]
    for directory in Path(root).iterdir():
        if directory.is_symlink() or not directory.is_dir():continue
        try:
            if str(UUID(directory.name))!=directory.name:continue
            path=directory/'failure.json'
            if path.is_symlink() or not path.is_file():continue
            raw=json.loads(path.read_text())
            if not isinstance(raw,dict):continue
            if raw.get('run_id')!=directory.name or raw.get('status')!='failed':continue
            parent=raw.get('parent_design_id')
            if parent is not None:parent=str(UUID(parent))
            archive=directory/'failed-solver-artifacts.zip'
            records.append({'run_id':directory.name,'parent_id':parent,'reason':failure_reason(archive),'stage':str(raw.get('stage','unknown'))[:80],'retained_at_epoch':path.stat().st_mtime,'has_solver_archive':archive.is_file() and not archive.is_symlink(),'provenance':'failure_record_not_registered_success'})
        except (ValueError,TypeError,OSError):continue
    return sorted(records,key=lambda r:(r['retained_at_epoch'],r['run_id']),reverse=True)[:limit]
