"""Read-only discovery of retained failures, separate from verified saved runs."""
import json
from pathlib import Path
from uuid import UUID

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
            records.append({'run_id':directory.name,'parent_id':parent,'stage':str(raw.get('stage','unknown'))[:80],'retained_at_epoch':path.stat().st_mtime,'has_solver_archive':archive.is_file() and not archive.is_symlink(),'provenance':'failure_record_not_registered_success'})
        except (ValueError,TypeError,OSError):continue
    return sorted(records,key=lambda r:(r['retained_at_epoch'],r['run_id']),reverse=True)[:limit]
