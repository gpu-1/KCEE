"""Source-linked recorded investigations, separate from registered study artifacts."""
import hashlib,json,math,re
from pathlib import Path
from kcee.provenance import IntegrityError
FILES=('finer-mesh-exploration.json','root-refinement-exploration.json')

ARCHIVES={
    (FILES[0],None):'finer-solve-20261014/exploratory-artifacts.zip',
    (FILES[1],.9):'root-refinement-20261014/root-0.9/solver-artifacts.zip',
    (FILES[1],.75):'root-refinement-20261014/root-0.75/solver-artifacts.zip',
}

def verify_exploratory_archive(root,name,target,expected):
    if root is None:return 'not_available'
    relative=ARCHIVES.get((name,target))
    if relative is None:raise ValueError('Unsupported exploratory archive identity')
    root=Path(root);path=root/relative
    try:path.resolve().relative_to(root.resolve())
    except ValueError:raise IntegrityError('Exploratory archive escapes its directory')
    if path.is_symlink():raise IntegrityError('Exploratory archive is a symbolic link')
    if not path.is_file():return 'not_available'
    if path.stat().st_size>512*1024*1024:raise IntegrityError('Exploratory archive exceeds verification limit')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=expected:raise IntegrityError('Exploratory archive hash mismatch')
    return 'verified'

def recorded_explorations(directory,record,archive_root=None):
    items=[]
    for name in FILES:
        path=Path(directory)/name
        if not path.is_file():continue
        raw=path.read_bytes();report=json.loads(raw)
        if report.get('run_id')!=str(record['id']):continue
        if report.get('manifest_sha256')!=record['manifest_sha256'] or report.get('source_stl_sha256')!=record['manifest']['artifacts']['bracket.stl']:
            raise IntegrityError('Exploration source differs from selected saved study')
        candidates=[report['solve_1_3']] if name==FILES[0] else [c for c in report['candidates'] if c.get('status')=='solved_exploratory']
        rows=[]
        for candidate in candidates:
            s=candidate['summary'];archive=candidate['archive_sha256']
            if not re.fullmatch('[a-f0-9]{64}',archive):raise ValueError('Invalid exploration archive hash')
            numbers=[s['target_size_mm'],s['nodes'],s['elements'],s['tip_deflection_mm'],s['maximum_von_mises_MPa']]
            if not all(type(value) in (int,float) and math.isfinite(value) and value>0 for value in numbers):raise ValueError('Invalid exploration measurements')
            rows.append({'global_target_mm':s['target_size_mm'],'root_target_mm':s.get('root_local_target_mm'),'nodes':s['nodes'],'elements':s['elements'],'displacement_mm':s['tip_deflection_mm'],'peak_stress_MPa':s['maximum_von_mises_MPa'],'recorded_archive_sha256':archive,'archive_integrity':verify_exploratory_archive(archive_root,name,s.get('root_local_target_mm'),archive)})
        items.append({'name':name,'report_sha256':hashlib.sha256(raw).hexdigest(),'rows':rows,'report':report})
    return items
