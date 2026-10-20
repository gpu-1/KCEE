"""Strict, source-replayed verification of portable regional JSON snapshots."""
import hashlib,json,math
from datetime import datetime,timezone
from kcee.provenance import IntegrityError
MAX_BYTES=2*1024*1024
SCHEMA='native-regional-verification-v1'
def parse(raw):
 if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:raise ValueError('Choose a regional JSON export up to 2 MB')
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate JSON key')
   d[k]=v
  return d
 def constant(v):raise ValueError('Nonfinite JSON number')
 try:data=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)
 except (UnicodeError,RecursionError,json.JSONDecodeError) as e:raise ValueError('Malformed regional JSON') from e
 count=0
 def walk(v,depth=0):
  nonlocal count
  count+=1
  if depth>24 or count>50000:raise ValueError('Regional JSON structure exceeds limit')
  if type(v) is float and not math.isfinite(v):raise ValueError('Nonfinite JSON number')
  if isinstance(v,dict):
   for x in v.values():walk(x,depth+1)
  elif isinstance(v,list):
   for x in v:walk(x,depth+1)
 walk(data)
 if not isinstance(data,dict) or data.get('schema')!='native-regional-loads-v1':raise ValueError('Unsupported regional export schema')
 return data

def differences(snapshot,actual):
 # Canonical JSON preserves scalar types, including booleans versus numbers.
 canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
 fields=sorted(k for k in actual if k not in snapshot or canonical(snapshot[k])!=canonical(actual[k]))
 if set(snapshot)-set(actual):fields.append('unexpected_fields')
 return fields

def verify(root,identifier,registry,raw):
 from kcee.regional_forces import audit
 snapshot=parse(raw)
 report={'schema':SCHEMA,'checked_at':datetime.now(timezone.utc).isoformat(),'file_sha256':hashlib.sha256(raw).hexdigest(),'file_size_bytes':len(raw),'selected_report_run_id':str(identifier),'source_evidence':'not_checked','integrity':'not_verified','mismatched_fields':[], 'engineering_acceptance':'pending','limits':'Checks reproduce local source evidence and compare the entire regional snapshot. They do not prove authorship, physical accuracy or mesh convergence. Source reports and files are not modified.'}
 if snapshot.get('report_run_id')!=str(identifier):
  report.update(integrity='source_mismatch',mismatched_fields=['report_run_id']);return report
 try:actual=audit(root,identifier,registry)
 except KeyError:report.update(integrity='source_unavailable');return report
 except IntegrityError:report.update(integrity='source_integrity_failed');return report
 except ValueError:report.update(integrity='source_replay_failed');return report
 changed=differences(snapshot,actual)
 report.update(source_evidence='reproduced',report_manifest_sha256=actual['report_manifest_sha256'],native_archive_sha256=actual['native_archive_sha256'],implementation_sha256=actual['implementation_sha256'],source_cases=len(actual['cases']),source_manifests=[{'run_id':c['run_id'],'manifest_sha256':c['manifest_sha256']} for c in actual['cases']],mismatched_fields=changed)
 report['integrity']='matches_reproduced_sources' if not changed else 'snapshot_differs'
 report['all_source_solver_checks']=all(all(c['source_checks'].values()) and c['bore_checks_pass'] for c in actual['cases'])
 return report
