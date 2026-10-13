"""Read-only stress/element diagnostic report for a verified saved bracket."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.provenance import verify_directory
from kcee.stress_diagnostics import diagnose
parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
directory=Path(args.directory);manifest,digest=verify_directory(directory,expected_digest=args.manifest_sha256)
report=diagnose(directory/'fea-artifacts.zip');report.update({'run_id':directory.name,'manifest_sha256':digest,'archive_sha256':manifest['artifacts']['fea-artifacts.zip']})
with Path(args.output).open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report,indent=2))
