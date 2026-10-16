"""Matched bore-local refinement, retaining the original far-mesh comparison."""
import csv,hashlib,json,math,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from kcee.bracket_flow import domain_spec
from kcee.flow_sampling import PROBES,common_sampling
from kcee.flow_refinement import controlled_inputs
LIMITS=[
 'This is a two-by-two background-mesh/bore-level sensitivity study in the fixed far domain. It is not an asymptotic convergence sequence or a mesh-independence acceptance test.',
 'Level 5 halves nominal bore-region spacing relative to level 4 at the same background mesh. Snapping and transition-cell topology also change; this is not an isolated pressure-equation error estimate.',
 'All referenced pressures subtract the fixed upstream probe within each case and use inlet dynamic scale 0.00005 m²/s². The upstream reference can itself be boundary-sensitive.',
 'The native VTK audit exposes centres only for decomposed cells. Coverage and each probe support coverage are reported. It does not provide complete native C or native probe interpolation, and exported coordinates include ASCII float rounding.',
 'A separate compact-stencil audit reuses the exact saved fields, positions and wall visibility, minimizing maximum support radius in the same bounded candidate pool. It is diagnostic custom interpolation, not a native sampler or replacement for production probes.',
 'Custom positive tetrahedral interpolation, finite bore-opening rays, no prism layers and exploratory steady laminar Re=6 conditions remain. Engineering acceptance and joint mesh/domain independence are unestablished.'
]

def summary(sources,audits):
 sampling=common_sampling(sources)
 if len(sources)!=4 or [(s['flow']['mesh_name'],s['flow']['inputs']['bore_refinement']['level']) for s in sources]!=[('medium',4),('fine',4),('medium',5),('fine',5)]:raise ValueError('Use medium/fine level 4 followed by medium/fine level 5')
 if len({s['run_id'] for s in sources})!=4:raise ValueError('Use four distinct source cases')
 rows=[];common=None;source_hash=None
 for s in sources:
  f=s['flow'];name=f['mesh_name'];inputs=controlled_inputs(f);inputs['bore_refinement']=dict(inputs['bore_refinement']);inputs['bore_refinement'].pop('level',None)
  if common is None:common=inputs;source_hash=f['source']['source_stl_sha256']
  spec=domain_spec(name,'far')
  if inputs!=common or f['source']['source_stl_sha256']!=source_hash or f.get('domain_name')!='far' or f['inputs']['background_cells']!=spec['background_cells'] or any(f['inputs'][k]!=spec[k] for k in ('domain_min_m','domain_max_m')):raise ValueError('Pressure-study physics, source, domain or mesh differ')
  if f.get('field_position_basis')!='triangulated_polyhedral_volume_centroids':raise ValueError('Use centroid-based probes')
  probes=f['fixed_probes']
  if [(p['name'],p['requested_position_m']) for p in probes]!=[(n,list(p)) for n,p in PROBES] or not all(p.get('available') for p in probes) or not all(math.isfinite(v) for p in probes for v in [*p['velocity_m_s'],p['kinematic_pressure_m2_s2']]):raise ValueError('Missing or invalid fixed probes')
  a=audits.get(s['run_id'])
  if not a or a['source_archive_sha256']!=s['archive_sha256'] or a['total_cells']!=f['cells'] or not 0<a['native_centres_exported']<=f['cells']:raise ValueError('Native audit source or coverage differs')
  anchor=probes[0]['kinematic_pressure_m2_s2']
  rows.append({'run_id':s['run_id'],'manifest_sha256':s['manifest_sha256'],'mesh_name':name,'bore_level':f['inputs']['bore_refinement']['level'],'nominal_bore_cell_m':f['inputs']['bore_refinement']['nominal_cell_m'],'cells':f['cells'],'solver_checks':f['checks'],'bore_verification':f['bore_verification'],'mesh_quality':f['mesh'],'upstream_kinematic_pressure_m2_s2':anchor,'probes':[dict(p,pressure_minus_upstream_m2_s2=p['kinematic_pressure_m2_s2']-anchor) for p in probes],'native_audit':a,'compact_probes':[dict(p,pressure_minus_upstream_m2_s2=p['kinematic_pressure_m2_s2']-a['stencil_audit']['compact_probes'][0]['kinematic_pressure_m2_s2']) for p in a['stencil_audit']['compact_probes']]})
 def change(a,b,label):
  probes=[{'name':x['name'],'referenced_pressure_change_m2_s2':y['pressure_minus_upstream_m2_s2']-x['pressure_minus_upstream_m2_s2'],'velocity_vector_change_m_s':math.dist(x['velocity_m_s'],y['velocity_m_s'])} for x,y in zip(a['probes'],b['probes'])]
  return {'label':label,'from_run_id':a['run_id'],'to_run_id':b['run_id'],'probes':probes,'maximum_velocity_change_normalized_by_inlet':max(p['velocity_vector_change_m_s'] for p in probes)/.01,'maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale':max(abs(p['referenced_pressure_change_m2_s2']) for p in probes)/.00005,'largest_pressure_probe':max(probes,key=lambda p:abs(p['referenced_pressure_change_m2_s2']))['name']}
 compact=[dict(s,probes=s['compact_probes']) for s in rows]
 return {'sampling':sampling,'compact_background_mesh_changes':[change(compact[0],compact[1],'Level 4'),change(compact[2],compact[3],'Level 5')],'compact_local_bore_changes':[change(compact[0],compact[2],'Medium'),change(compact[1],compact[3],'Fine')],'schema':'kcee.bracket-flow-pressure.v1','source_stl_sha256':source_hash,'common_inputs':common,'studies':rows,'background_mesh_changes':[change(rows[0],rows[1],'Level 4'),change(rows[2],rows[3],'Level 5')],'local_bore_changes':[change(rows[0],rows[2],'Medium'),change(rows[1],rows[3],'Fine')],'checks':{'all_solver_checks':all(all(s['solver_checks'].values()) for s in rows),'all_bore_opening_gates':all(s['bore_verification']['all_pass'] for s in rows),'refined_cases_have_more_cells':rows[2]['cells']>rows[0]['cells'] and rows[3]['cells']>rows[1]['cells'],'native_audits_bound_to_source_archives':True},'mesh_independence':'not_established','engineering_acceptance':'pending','limits':LIMITS}

def save(root,parent,record,sources,audits):
 data=summary(sources,audits);root=Path(root);dest=root/str(uuid.uuid4());dest.mkdir()
 for n in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/n,dest/n)
 req=json.loads((dest/'requirements.json').read_text());req['flow_pressure']={'source_runs':[s['run_id'] for s in sources]};(dest/'requirements.json').write_text(json.dumps(req,indent=2))
 status='exploratory_bracket_flow_pressure_recorded_not_engineering_validated'
 for name,value in [('cfd.json',data),('result.json',{'kind':'bracket_flow_pressure','validation_status':status,'geometry_backend':'PicoGK / OpenFOAM bore pressure sensitivity','pressure_study':data,'assumptions':LIMITS}),('voice-summary.json',{'text':'Bore pressure sensitivity study recorded. Review the matched comparisons; mesh independence remains unestablished.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 lines=['# Bore pressure sensitivity verification','','Source STL SHA-256: '+data['source_stl_sha256'],'','Mesh independence is not established. Engineering acceptance is pending.','','## Matched cases','| Mesh | Bore level | Cells | Nominal bore size (mm) | Native centre coverage | Source run |','|---|---|---|---|---|---|']
 for s in data['studies']:lines.append(f"| {s['mesh_name']} | {s['bore_level']} | {s['cells']} | {s['nominal_bore_cell_m']*1000:.6f} | {s['native_audit']['coverage_fraction']*100:.3f}% | {s['run_id']} |")
 for title,key in [('Background mesh changes (medium → fine)','background_mesh_changes'),('Bore refinement changes (level 4 → 5)','local_bore_changes'),('Compact-stencil background mesh audit','compact_background_mesh_changes'),('Compact-stencil local bore audit','compact_local_bore_changes')]:
  lines+=['','## '+title,'| Pair | Max velocity / inlet | Max referenced pressure / inlet dynamic scale | Largest pressure probe |','|---|---|---|---|']
  for c in data[key]:lines.append(f"| {c['label']} | {c['maximum_velocity_change_normalized_by_inlet']*100:.5f}% | {c['maximum_referenced_pressure_change_normalized_by_inlet_dynamic_scale']*100:.5f}% | {c['largest_pressure_probe']} |")
 original_fine=data['studies'][1];saved=original_fine['probes'][0];compact=original_fine['compact_probes'][0]
 lines+=['','## Upstream reference stencil audit',f"Original fine/level-4 upstream support radius: {saved['maximum_support_distance_m']*1000:.6f} mm saved versus {compact['maximum_support_distance_m']*1000:.6f} mm compact.",f"Its raw upstream kinematic-pressure shift (compact minus saved) is {compact['kinematic_pressure_m2_s2']-saved['kinematic_pressure_m2_s2']:.12g} m²/s². Every referenced probe subtracts this upstream value, so a reference-sampling change propagates through the comparison without requiring a local bore-pressure change."]
 for a,b in zip(original_fine['probes'],original_fine['compact_probes']):
  if a['name']=='upright bore 1':lines.append(f"At upright bore 1, the raw same-field pressure shift is {b['kinematic_pressure_m2_s2']-a['kinematic_pressure_m2_s2']:.12g} m²/s². Inspect the compact and saved pair tables together; sampling sensitivity is not a pressure-error bound or proof of convergence.")
 lines+=['','## Numerical checks',json.dumps(data['checks'],indent=2),'','## Native sampling audit','OpenFOAM foamToVTK decomposition centres are matched to original cellID. Standard-cell centres are not exported. See cfd.json for per-probe coverage, native positions, export binary/hash/log and source-archive hashes. This partial audit cannot validate all bore probe locations.','', '## Source manifests',*['- '+s['run_id']+': '+s['manifest_sha256'] for s in sources],'','## Limits',*['- '+s for s in LIMITS]]
 (dest/'report.md').write_text('\n'.join(lines)+'\n')
 with (dest/'verification.csv').open('w',newline='') as stream:
  w=csv.writer(stream);w.writerow(['run_id','manifest_sha256','mesh','bore_level','cells','probe','raw_kinematic_pressure_m2_s2','upstream_kinematic_pressure_m2_s2','pressure_minus_upstream_m2_s2','speed_m_s','maximum_support_distance_m'])
  for s in data['studies']:
   for p in s['probes']:w.writerow([s['run_id'],s['manifest_sha256'],s['mesh_name'],s['bore_level'],s['cells'],p['name'],p['kinematic_pressure_m2_s2'],s['upstream_kinematic_pressure_m2_s2'],p['pressure_minus_upstream_m2_s2'],p['speed_m_s'],p['maximum_support_distance_m']])
 manifest={'schema_version':1,'kind':'bracket_flow_pressure','run_id':dest.name,'parent_design_id':str(parent),'created_at':datetime.now(timezone.utc).isoformat(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sampling_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_sampling.py').read_bytes()).hexdigest(),'native_audit_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_native.py').read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'validation_status':status,'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}};(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest
