"""Read-only verification of preview fields against a saved solver archive."""
import argparse,hashlib,io,json,math,sys
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.fields import displacement_surface

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--base-url',default='http://localhost:8000');args=parser.parse_args()
    from uuid import UUID
    run_id=str(UUID(args.run_id))
    def fetch(path):
        with urlopen(args.base_url+path,timeout=60) as response:return response.read()
    def read(path):return json.loads(fetch(path))
    record=read('/runs/'+run_id)
    if read('/runs/'+run_id+'/verify')['integrity']!='verified':raise ValueError('Run integrity check failed')
    if record['manifest'].get('kind')!='bracket_structural':raise ValueError('Expected bracket structural run')
    archive=fetch('/artifacts/'+run_id+'/fea-artifacts.zip');digest=hashlib.sha256(archive).hexdigest()
    if digest!=record['manifest']['artifacts']['fea-artifacts.zip']:raise ValueError('Downloaded archive hash mismatch')
    expected=displacement_surface(io.BytesIO(archive));actual=read('/runs/'+run_id+'/displacement-surface')
    if actual.pop('source_archive_sha256')!=digest:raise ValueError('Preview archive identity mismatch')
    for key in expected:
        if key=='von_mises_MPa':
            if len(actual[key])!=len(expected[key]) or not all(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12) for a,b in zip(actual[key],expected[key])):raise ValueError('Preview stress differs from archive')
        elif key.startswith('maximum_'):
            if not math.isclose(actual[key],expected[key],rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Preview maximum differs from archive')
        elif actual[key]!=expected[key]:raise ValueError('Preview differs from archived solver fields: '+key)
    edges={};volume=0
    for triangle in actual['triangles']:
        a,b,c=[actual['positions'][i] for i in triangle]
        volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for i in range(3):
            start,end=triangle[i],triangle[(i+1)%3];key=tuple(sorted((start,end)))
            count,balance=edges.get(key,(0,0));edges[key]=(count+1,balance+(1 if start<end else -1))
    if any(count!=2 or balance!=0 for count,balance in edges.values()):raise ValueError('Preview surface is not closed and consistently oriented')
    result=read('/artifacts/'+run_id+'/result.json');fine=result['fea']['mesh_study'][-1]
    if not math.isclose(volume,fine['volume_mm3'],rel_tol=1e-8):raise ValueError('Preview surface volume differs from solver volume')
    print(json.dumps({'run_id':run_id,'archive_sha256':digest,'surface_nodes':len(actual['positions']),'surface_triangles':len(actual['triangles']),'closed_oriented_surface':True,'surface_volume_mm3':volume,'maximum_nodal_displacement_mm':actual['maximum_displacement_mm'],'maximum_averaged_surface_stress_MPa':actual['maximum_surface_von_mises_MPa'],'archive_field_agreement':'geometry and vectors exact; derived magnitudes within 1e-12 tolerance','engineering_validation':'pending'},indent=2))

if __name__=='__main__':main()
