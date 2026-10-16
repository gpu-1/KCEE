"""Verify artifacts against an independently stored manifest."""
import hashlib
import json
import re
from pathlib import Path
from uuid import UUID

REQUIRED = {'requirements.json','bracket.stl','result.json','voice-summary.json','report.md'}

class IntegrityError(ValueError):
    pass

def verify_directory(directory, expected_manifest=None, expected_digest=None):
    directory=Path(directory)
    if directory.is_symlink(): raise IntegrityError('Run directory must not be a symlink')
    path=directory/'manifest.json'
    if path.is_symlink(): raise IntegrityError('Manifest must not be a symlink')
    try:
        raw=path.read_bytes(); manifest=json.loads(raw)
        if not isinstance(manifest,dict): raise IntegrityError('Invalid manifest')
        digest=hashlib.sha256(raw).hexdigest()
        if expected_digest is not None and digest!=expected_digest:
            raise IntegrityError('Manifest hash differs from database record')
        if expected_manifest is not None and manifest!=expected_manifest:
            raise IntegrityError('Manifest differs from database record')
        if str(UUID(manifest['run_id']))!=directory.name: raise IntegrityError('Run identity mismatch')
        if manifest['schema_version']!=1: raise IntegrityError('Unsupported manifest version')
        artifacts=manifest['artifacts']
        if not isinstance(artifacts,dict) or (not (manifest.get('kind') in ('bracket_flow_refinement','bracket_flow_domain') and set(artifacts)==REQUIRED|{'geometry-request.json','geometry.json','cfd.json','verification.csv'}) and not (manifest.get('kind')=='bracket_flow' and set(artifacts)==REQUIRED|{'geometry-request.json','geometry.json','cfd.json','field.csv','cfd-artifacts.zip'}) and not (manifest.get('kind')=='cfd_vortex' and set(artifacts) in (REQUIRED|{'cfd.json','field.csv','cfd-artifacts.zip'},REQUIRED|{'cfd.json','field.csv','cfd-artifacts.zip','verification.csv'})) and not (manifest.get('kind')=='cfd_benchmark' and set(artifacts)==REQUIRED|{'cfd.json','velocity.csv'}) and set(artifacts) not in (REQUIRED,REQUIRED|{'geometry-request.json','geometry.json'},REQUIRED|{'fea.json','fea-artifacts.zip'},REQUIRED|{'thermal.json','temperature.csv'},REQUIRED|{'geometry-request.json','geometry.json','thermal.json','thermal-artifacts.zip','temperature.csv'},REQUIRED|{'geometry-request.json','geometry.json','fea.json','fea-artifacts.zip'})):
            raise IntegrityError('Unexpected artifact inventory')
        for name,expected in artifacts.items():
            if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):
                raise IntegrityError('Invalid artifact digest')
            artifact=directory/name
            if artifact.is_symlink() or not artifact.is_file(): raise IntegrityError('Missing or unsafe artifact: '+name)
            if hashlib.sha256(artifact.read_bytes()).hexdigest()!=expected:
                raise IntegrityError('Artifact hash mismatch: '+name)
        if {p.name for p in directory.iterdir()}!=set(artifacts)|{'manifest.json'}:
            raise IntegrityError('Unexpected files in run directory')
        return manifest,digest
    except (OSError,KeyError,TypeError,json.JSONDecodeError,ValueError) as exc:
        if isinstance(exc,IntegrityError): raise
        raise IntegrityError('Unreadable or malformed run record') from exc
