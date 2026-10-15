"""Read-only presentation of backup receipts; never claims a fresh integrity check."""
import json
from datetime import datetime, timezone
from pathlib import Path

def recorded_status(directory):
    directory=Path(directory)
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'backup':None,'restore':None,'warnings':[]}
    for kind,pattern in [('backup','*.zip.receipt.json'),('restore','*restore-verification.json')]:
        try:
            candidates=list(directory.glob(pattern))
            if len(candidates)>100:raise ValueError('Too many status records (maximum 100)')
            candidates=sorted(candidates,key=lambda p:p.stat().st_mtime,reverse=True)
            if not candidates:continue
            path=candidates[0]
            if path.is_symlink() or path.stat().st_size>256*1024:raise ValueError('Invalid status record')
            data=json.loads(path.read_text())
            verification=data if kind=='backup' else data['verification']
            counts=verification['counts']
            if not isinstance(counts,dict) or not all(isinstance(k,str) and isinstance(v,int) and not isinstance(v,bool) and v>=0 for k,v in counts.items()):raise ValueError('Invalid counts')
            notes=verification.get('review_notes')
            summary={'record_name':path.name,'record_updated_at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'counts':counts,'review_notes_verified':bool(isinstance(notes,dict) and notes.get('integrity')=='verified'),'status':'recorded'}
            if kind=='backup':
                digest=data['bundle_sha256']
                if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('Invalid bundle fingerprint')
                summary.update(bundle_name=Path(data['bundle']).name,bundle_sha256=digest)
                bundle=directory/summary['bundle_name']
                summary['bundle_present']=bundle.is_file() and not bundle.is_symlink()
            else:
                if verification.get('integrity')!='verified':raise ValueError('Restore verification did not pass')
                summary.update(status='verification_recorded',native_setup_required=data.get('native_setup_required',True) is not False)
            result[kind]=summary
        except (OSError,ValueError,KeyError,TypeError):
            result['warnings'].append(kind+' status record is unavailable or invalid; no older record was substituted.')
    return result
