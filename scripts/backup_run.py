"""Offline single-run export/restore with externally trusted checksum inputs."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kcee.run_backup import export_run,restore_run
parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='command',required=True)
export=commands.add_parser('export');export.add_argument('directory');export.add_argument('output');export.add_argument('--manifest-sha256',required=True)
restore=commands.add_parser('restore');restore.add_argument('bundle');restore.add_argument('destination');restore.add_argument('--bundle-sha256',required=True);restore.add_argument('--manifest-sha256',required=True)
args=parser.parse_args()
result=export_run(args.directory,args.output,args.manifest_sha256) if args.command=='export' else restore_run(args.bundle,args.destination,args.bundle_sha256,args.manifest_sha256)
print(json.dumps(result,indent=2))
