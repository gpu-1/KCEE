"""Source-linked recorded investigations, separate from registered study artifacts."""
import hashlib,json,math,re
from pathlib import Path
from kcee.provenance import IntegrityError
FILES=('finer-mesh-exploration.json','root-refinement-exploration.json')

def recorded_explorations(directory,record):
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
            rows.append({'global_target_mm':s['target_size_mm'],'root_target_mm':s.get('root_local_target_mm'),'nodes':s['nodes'],'elements':s['elements'],'displacement_mm':s['tip_deflection_mm'],'peak_stress_MPa':s['maximum_von_mises_MPa'],'recorded_archive_sha256':archive})
        items.append({'name':name,'report_sha256':hashlib.sha256(raw).hexdigest(),'rows':rows,'report':report})
    return items
