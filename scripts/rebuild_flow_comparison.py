"""Create a new registered pressure comparison from three verified source studies.

Run inside the API environment so the registry and artifact root are available.
Existing source studies and comparisons are never modified.
"""
import argparse,json
from pathlib import Path
from uuid import UUID


def rebuild(root,parent_id,study_ids,registry):
    from kcee.flow_refinement import save_comparison
    from kcee.provenance import verify_directory
    root=Path(root);parent_id=str(UUID(str(parent_id)))
    if len(study_ids)!=3 or len(set(map(str,study_ids)))!=3:
        raise ValueError('Provide three distinct coarse, medium and fine study IDs')
    registry.verify(root,parent_id);record=registry.get(parent_id);studies=[]
    for value in study_ids:
        run_id=str(UUID(str(value)));registry.verify(root,run_id)
        manifest,digest=verify_directory(root/run_id)
        if manifest.get('parent_design_id')!=parent_id or manifest.get('source_parent_manifest_sha256')!=record['manifest_sha256']:
            raise ValueError('Source study parent identity differs from the verified parent')
        result=json.loads((root/run_id/'result.json').read_text())
        flow=result.get('flow',{})
        if result.get('kind')!='bracket_flow' or flow.get('field_position_basis')!='triangulated_polyhedral_volume_centroids' or flow.get('inputs',{}).get('maximum_iterations')!=1500:
            raise ValueError('Use the current centroid-based 1500-iteration bracket-flow studies')
        studies.append({'run_id':run_id,'manifest_sha256':digest,'flow':flow})
    dest=save_comparison(root,parent_id,record,studies)
    registry.register(dest);registry.verify(root,dest.name)
    return dest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs-dir',default='/data/runs')
    parser.add_argument('--parent',required=True)
    parser.add_argument('--studies',nargs=3,required=True,metavar='RUN_ID')
    args=parser.parse_args()
    from kcee.registry import Registry
    dest=rebuild(args.runs_dir,args.parent,args.studies,Registry())
    print(json.dumps({'run_id':dest.name,'operation':'new_comparison_from_verified_sources'}))


if __name__=='__main__':main()
