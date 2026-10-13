"""Native bracket voxel refinement study; does not establish FEA convergence."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.demo import DEFAULT,run
from kcee.provenance import verify_directory
from check_picogk import check_mesh

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False);rows=[]
    for size in (.75,.5,.35):
        request=json.loads(DEFAULT.read_text());request['geometry_options']={'voxel_size_mm':size}
        path=output/f'requirements-{size}.json';path.write_text(json.dumps(request,indent=2))
        dest=run(output/'runs',path,'picogk');manifest,digest=verify_directory(dest)
        topology,volume=check_mesh(dest/'bracket.stl')
        if topology!=-6:raise ValueError('Four-hole topology not preserved')
        metadata=json.loads((dest/'geometry.json').read_text())
        rows.append({'run_id':dest.name,'manifest_sha256':digest,'voxel_size_mm':size,'voxel_volume_mm3':metadata['volume_mm3'],'surface_volume_mm3':volume,'triangle_count':metadata['triangle_count'],'euler_characteristic':topology,'stl_sha256':manifest['artifacts']['bracket.stl']})
        print(f'Completed {size} mm voxel bracket',flush=True)
    voxel_change=abs(rows[-1]['voxel_volume_mm3']/rows[-2]['voxel_volume_mm3']-1)
    surface_change=abs(rows[-1]['surface_volume_mm3']/rows[-2]['surface_volume_mm3']-1)
    result={'schema_version':1,'geometry':'same default four-hole bracket; selected thickness 3.5 mm','study':rows,'last_voxel_volume_change':voxel_change,'last_surface_volume_change':surface_change,'status':'geometry_refinement_measured_not_engineering_validated','limitations':['Three resolutions do not prove asymptotic geometry convergence','Volume agreement does not establish local feature accuracy','FEA is not repeated at these resolutions; stress convergence remains pending']}
    (output/'geometry-refinement.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
