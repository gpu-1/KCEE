"""Measure mid-thickness radial bore sections in a recorded refinement study."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.geometry_measure import hole_sections
from kcee.provenance import verify_directory
parser=argparse.ArgumentParser();parser.add_argument('study');parser.add_argument('--output',required=True);args=parser.parse_args()
path=Path(args.study);study=json.loads(path.read_text());rows=[]
for row in study['study']:
    directory=path.parent/'runs'/row['run_id'];verify_directory(directory,expected_digest=row['manifest_sha256'])
    request=json.loads((directory/'geometry-request.json').read_text())
    if request['geometry_mm']!={'length':60,'width':30,'height':40,'thickness':3.5} or request['hole_diameter_mm']!=5 or not request['mounting_holes']:raise ValueError('Unsupported geometry for default bore measurement')
    rows.append({'voxel_size_mm':row['voxel_size_mm'],'stl_sha256':row['stl_sha256'],'holes':[hole for section in (.875,1.75,2.625) for hole in hole_sections(directory/'bracket.stl',section)]})
result={'study':rows,'method':'Quarter-, mid-, and three-quarter-thickness plane intersections; twice radial extrema about nominal bore center, including chord interiors','limitations':['Radial envelopes are not fitted diameters or manufacturing acceptance','Only default 60×30×40 bracket with 3.5 mm thickness and 5 mm holes supported','Entry/exit sections, feature positions and root transition accuracy remain unmeasured'],'status':'geometry_measurement_not_engineering_validated'}
with Path(args.output).open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
