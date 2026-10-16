"""Gauge-invariant pressure contrasts and targeted far/outer boundary sensitivity."""
import csv,hashlib,json,math,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from kcee.bracket_flow import LOCAL_PROFILE,domain_spec
from kcee.flow_local_refinement import summary as local_summary
from kcee.flow_sampling import COMPACT,PROBES,common_sampling
from kcee.provenance import verify_directory
ANCHOR='above'
PAIRS=[('wake gradient','wake','far wake'),('below vs above','below','above'),('base bores','base bore 2','base bore 1'),('upright bores','upright bore 2','upright bore 1')]
LIMITS=[
 'Pressure decomposition is algebraic: change of (p_probe-p_upstream) equals change of (p_probe-p_above) plus change of (p_above-p_upstream). It does not uniquely assign physical error to a reference or region.',
 'Local contrasts and both referenced fields are gauge invariant. Raw outlet-referenced pressures and the upstream pressure are retained as diagnostics, not cross-domain physical pressure errors.',
 'Only targeted medium resolution is expanded from far to outer. Background spacing and integer-cell alignment, physical refinement boxes, bore level 4, physics and Compact v1 remain fixed. Snapped topology can still change.',
 'This is one additional boundary-distance pair, not a full mesh/domain Cartesian study, continuum boundary-error estimate, asymptotic convergence proof or acceptance threshold.',
 'The above probe is another finite-domain sample, not an exact or unaffected reference. Local probe pairs do not isolate boundary effects from discretization or interpolation effects.',
 'Custom triangulated-polyhedron centroids, bounded-candidate interpolation, finite bore rays, absent prism layers and exploratory steady laminar Re=6 conditions retain their limitations. Mesh/domain independence and engineering acceptance remain unestablished.'
]

def summary(sources):
 if len(sources) not in (5,6) or len({s['run_id'] for s in sources})!=len(sources):raise ValueError('Use four local-study cases, medium outer and optional fine outer')
 base=local_summary(sources[:4]);sampling=common_sampling(sources)
 if sampling['version']!=COMPACT:raise ValueError('Reference study requires Compact v1')
 far=sources[2]['flow'];outer=sources[4]['flow'];spec=domain_spec('medium','outer')
 if outer.get('mesh_name')!='medium' or outer.get('domain_name')!='outer' or outer['inputs'].get('local_refinement_profile')!=LOCAL_PROFILE:raise ValueError('Use targeted medium outer case')
 omit=('domain_min_m','domain_max_m','background_cells')
 if {k:v for k,v in far['inputs'].items() if k not in omit}!={k:v for k,v in outer['inputs'].items() if k not in omit} or outer['source']['source_stl_sha256']!=base['source_stl_sha256']:raise ValueError('Outer case physics, profile or source differs')
 if any(outer['inputs'][k]!=spec[k] for k in omit):raise ValueError('Outer bounds/background differ')
 if outer.get('field_position_basis')!='triangulated_polyhedral_volume_centroids' or outer['mesh'].get('targeted_refinement')!=far['mesh']['targeted_refinement']:raise ValueError('Outer sampling basis or refinement differs')
 fine_audit=None
 if len(sources)==6:
  f=sources[5]['flow'];ff=sources[3]['flow'];fine_spec=domain_spec('fine','outer')
  if f.get('mesh_name')!='fine' or f.get('domain_name')!='outer' or f['inputs'].get('local_refinement_profile')!=LOCAL_PROFILE:raise ValueError('Use targeted fine outer case')
  if f['source']['source_stl_sha256']!=base['source_stl_sha256'] or f.get('field_position_basis')!='triangulated_polyhedral_volume_centroids':raise ValueError('Fine outer source or basis differs')
  if any(f['inputs'][k]!=fine_spec[k] for k in omit):raise ValueError('Fine outer domain/grid differs')
  special=omit+('bore_refinement','targeted_refinement')
  if {k:v for k,v in f['inputs'].items() if k not in special}!={k:v for k,v in ff['inputs'].items() if k not in special}:raise ValueError('Fine outer physics differs')
  for key,level in [('bore_refinement',4),('targeted_refinement',3)]:
   expected=dict(ff['inputs'][key],nominal_cell_m=max(fine_spec['background_spacing_m'])/2**level)
   if f['inputs'][key]!=expected or f['mesh'][key]!=expected:raise ValueError('Fine outer local recipe differs')
  prior=domain_spec('fine','far');h=fine_spec['background_spacing_m'];old=prior['background_spacing_m']
  fine_audit={'far_background_spacing_m':old,'outer_background_spacing_m':h,'relative_spacing_changes':[a/b-1 for a,b in zip(h,old)],'boundary_shift_in_far_cells':[(a-b)/d for a,b,d in zip(prior['domain_min_m'],fine_spec['domain_min_m'],old)],'spacing_and_alignment_preserved':False,'interpretation':'Fine domain pair changes spacing and alignment slightly; it is domain-plus-grid sensitivity, not isolated boundary sensitivity.'}
 rows=[]
 for source in sources:
  f=source['flow'];probes=f['fixed_probes']
  if [(p['name'],p['requested_position_m']) for p in probes]!=[(n,list(x)) for n,x in PROBES] or not all(p.get('available') for p in probes) or not all(math.isfinite(v) for p in probes for v in [p['kinematic_pressure_m2_s2'],*p['velocity_m_s']]):raise ValueError('Missing/nonfinite fixed reference probes')
  by={p['name']:p for p in probes};pressure=lambda n:by[n]['kinematic_pressure_m2_s2'];name=f['mesh_name']+' / '+f['inputs'].get('local_refinement_profile','baseline')+' / '+f['domain_name']
  rows.append({'label':name,'run_id':source['run_id'],'manifest_sha256':source['manifest_sha256'],'mesh_name':f['mesh_name'],'domain_name':f['domain_name'],'local_profile':f['inputs'].get('local_refinement_profile','baseline'),'cells':f['cells'],'inputs':f['inputs'],'solver_checks':f['checks'],'bore_verification':f['bore_verification'],'cell_position_audit':f['cell_position_audit'],'residuals':f['residuals'],'relative_boundary_mass_imbalance':f['relative_boundary_mass_imbalance'],'upstream_kinematic_pressure_m2_s2':pressure('upstream'),'anchor_minus_upstream_m2_s2':pressure(ANCHOR)-pressure('upstream'),'probes':[dict(p,pressure_minus_upstream_m2_s2=p['kinematic_pressure_m2_s2']-pressure('upstream'),pressure_minus_anchor_m2_s2=p['kinematic_pressure_m2_s2']-pressure(ANCHOR)) for p in probes],'local_pressure_pairs':[{'name':n,'first_probe':a,'second_probe':b,'difference_m2_s2':pressure(a)-pressure(b)} for n,a,b in PAIRS]})
 changes=[]
 pairs_to_compare=[(rows[0],rows[1],'Baseline mesh'),(rows[2],rows[3],'Targeted mesh'),(rows[2],rows[4],'Targeted far → outer')]
 if len(rows)==6:pairs_to_compare += [(rows[4],rows[5],'Outer medium → fine'),(rows[3],rows[5],'Fine far → outer + grid')]
 for a,b,label in pairs_to_compare:
  reference=b['anchor_minus_upstream_m2_s2']-a['anchor_minus_upstream_m2_s2'];probes=[]
  for x,y in zip(a['probes'],b['probes']):
   upstream=y['pressure_minus_upstream_m2_s2']-x['pressure_minus_upstream_m2_s2'];local=y['pressure_minus_anchor_m2_s2']-x['pressure_minus_anchor_m2_s2']
   if not math.isclose(upstream,local+reference,rel_tol=1e-12,abs_tol=1e-15):raise ValueError('Pressure decomposition identity failed')
   probes.append({'name':x['name'],'upstream_referenced_change_m2_s2':upstream,'local_anchor_change_m2_s2':local,'anchor_upstream_change_m2_s2':reference,'closure_residual_m2_s2':upstream-local-reference,'velocity_vector_change_m_s':math.dist(x['velocity_m_s'],y['velocity_m_s'])})
  pairs=[dict(x,change_m2_s2=y['difference_m2_s2']-x['difference_m2_s2']) for x,y in zip(a['local_pressure_pairs'],b['local_pressure_pairs'])]
  # Upstream is excluded from local-field maximum: it is explicitly the reference relation itself.
  local_probes=[p for p in probes if p['name']!='upstream']
  changes.append({'label':label,'from_run_id':a['run_id'],'to_run_id':b['run_id'],'probes':probes,'local_pressure_pairs':pairs,'maximum_upstream_referenced_change_normalized':max(abs(p['upstream_referenced_change_m2_s2']) for p in probes)/.00005,'maximum_local_anchor_change_normalized':max(abs(p['local_anchor_change_m2_s2']) for p in local_probes)/.00005,'anchor_upstream_change_normalized':reference/.00005,'maximum_local_pair_change_normalized':max(abs(p['change_m2_s2']) for p in pairs)/.00005,'maximum_velocity_change_normalized':max(p['velocity_vector_change_m_s'] for p in probes)/.01})
 fs=domain_spec('medium','far');aligned=all(math.isclose((a-b)/h,4,rel_tol=1e-12) for a,b,h in zip(fs['domain_min_m'],spec['domain_min_m'],fs['background_spacing_m'])) and all(math.isclose(a,b,rel_tol=1e-12) for a,b in zip(spec['background_spacing_m'],fs['background_spacing_m']))
 if not aligned:raise ValueError('Domain spacing/alignment differs')
 data={'schema':'kcee.bracket-flow-reference.v1','sampling':sampling,'source_stl_sha256':base['source_stl_sha256'],'local_anchor':ANCHOR,'normalization_m2_s2':.00005,'local_maximum_excludes':['upstream'],'local_pair_definitions':[{'name':n,'first_probe':a,'second_probe':b} for n,a,b in PAIRS],'studies':rows,'comparisons':changes,'checks':{'all_solver_checks':all(all(s['solver_checks'].values()) for s in rows),'all_bore_opening_gates':all(s['bore_verification']['all_pass'] for s in rows),'fixed_spacing_and_alignment':aligned,'decomposition_identity':True},'mesh_independence':'not_established','domain_convergence':'not_established','engineering_acceptance':'pending','limits':LIMITS}

 if len(rows)==6:
  medium,fine=changes[2],changes[4];probes=[]
  keys=('upstream_referenced_change_m2_s2','local_anchor_change_m2_s2','anchor_upstream_change_m2_s2')
  for a,b in zip(medium['probes'],fine['probes']):
   values={k:b[k]-a[k] for k in keys};values['closure_residual_m2_s2']=values[keys[0]]-values[keys[1]]-values[keys[2]]
   # Signed vector interaction, not subtraction of velocity magnitudes.
   by=[next(p for p in row['probes'] if p['name']==a['name']) for row in (rows[2],rows[3],rows[4],rows[5])]
   values['velocity_vector_change_m_s']=math.sqrt(sum(((by[3]['velocity_m_s'][i]-by[1]['velocity_m_s'][i])-(by[2]['velocity_m_s'][i]-by[0]['velocity_m_s'][i]))**2 for i in range(3)))
   probes.append(dict(values,name=a['name']))
  pairs=[dict(b,change_m2_s2=b['change_m2_s2']-a['change_m2_s2']) for a,b in zip(medium['local_pressure_pairs'],fine['local_pressure_pairs'])]
  data['schema']='kcee.bracket-flow-reference.v2';data['fine_grid_audit']=fine_audit
  data['interaction']={'label':'Mesh/domain interaction','source_run_ids':[r['run_id'] for r in rows[2:]],'source_manifest_sha256':[r['manifest_sha256'] for r in rows[2:]],'definition':'(fine outer - fine far) - (medium outer - medium far); equivalently outer mesh change minus far mesh change','probes':probes,'local_pressure_pairs':pairs,'maximum_upstream_referenced_change_normalized':max(abs(p[keys[0]]) for p in probes)/.00005,'maximum_local_anchor_change_normalized':max(abs(p[keys[1]]) for p in probes if p['name']!='upstream')/.00005,'anchor_upstream_change_normalized':probes[0][keys[2]]/.00005,'maximum_local_pair_change_normalized':max(abs(p['change_m2_s2']) for p in pairs)/.00005,'maximum_velocity_change_normalized':max(p['velocity_vector_change_m_s'] for p in probes)/.01}
  data['checks']['identical_domain_bounds_across_meshes']=all(rows[a]['inputs'][k]==rows[b]['inputs'][k] for a,b in [(2,3),(4,5)] for k in ('domain_min_m','domain_max_m'))
  data['limits']=[x for i,x in enumerate(LIMITS) if i not in (2,3)]+['Two meshes and two identical physical domains form a targeted 2×2 comparison. Medium domain spacing/alignment is fixed; fine domain spacing changes by up to about 0.513% and alignment changes. Fine boundary and interaction diagnostics include these grid changes; no isolated boundary-error claim.','Fine outer uses 65×49×53 background cells and a 350000-cell cap; worker memory/CPU limits and 1500 iterations remain fixed. Interaction is a signed difference of differences, not an error bound or independence proof.']
 return data


def save(root,parent,record,sources):
 data=summary(sources);root=Path(root)
 if data.get('fine_grid_audit'):
  import zipfile
  with zipfile.ZipFile(root/sources[5]['run_id']/'cfd-artifacts.zip') as archive:log=archive.read('snappyHexMesh.log').decode()
  reached='since reached limit' in log
  data['fine_mesh_capacity_audit']={'maximum_cells':350000,'refinement_limit_reached':reached,'evidence':'snappyHexMesh.log in fine outer source archive'}
  data['checks']['fine_mesh_refinement_not_cap_limited']=not reached
  if reached:data['limits'].append('Fine outer refinement reached its cell cap; requested local levels may be incomplete. Treat this as cap-limited mesh sensitivity.')
 dest=root/str(uuid.uuid4());dest.mkdir()
 for name in ('requirements.json','bracket.stl','geometry-request.json','geometry.json'):shutil.copy2(root/str(parent)/name,dest/name)
 req=json.loads((dest/'requirements.json').read_text());req['pressure_reference_study']={'source_runs':[s['run_id'] for s in sources],'local_anchor':ANCHOR,'pairs':PAIRS};(dest/'requirements.json').write_text(json.dumps(req,indent=2))
 status='exploratory_bracket_flow_reference_not_engineering_validated'
 for name,value in [('cfd.json',data),('result.json',{'kind':'bracket_flow_reference','validation_status':status,'geometry_backend':'PicoGK / OpenFOAM pressure contrasts','reference_study':data,'assumptions':LIMITS}),('voice-summary.json',{'text':'Pressure contrasts and targeted boundary sensitivity recorded. Review the reference decomposition and limits.','delivery':'artifact_only'})]:(dest/name).write_text(json.dumps(value,indent=2))
 lines=['# Pressure contrasts and targeted boundary sensitivity','','Source STL SHA-256: '+data['source_stl_sha256'],'','All changes use kinematic pressure in m²/s². Percent normalization is 0.00005 m²/s². Local anchor: above. Local-field maximum excludes upstream; local pairs have their own maximum.','','| Comparison | Upstream-reference max | Above-reference max | Above minus upstream change (signed) | Local pairs max | Velocity / inlet max |','|---|---|---|---|---|---|']
 for c in data['comparisons']:lines.append('| '+c['label']+' | '+' | '.join(f"{100*c[k]:.5f}%" for k in ('maximum_upstream_referenced_change_normalized','maximum_local_anchor_change_normalized','anchor_upstream_change_normalized','maximum_local_pair_change_normalized','maximum_velocity_change_normalized'))+' |')
 if data.get('fine_grid_audit'):lines+=['','## Fine grid audit',json.dumps(data['fine_grid_audit'],indent=2),'','## Fine mesh capacity audit',json.dumps(data['fine_mesh_capacity_audit'],indent=2),'','## Mesh/domain interaction (JSON/report; comparison CSV contains direct pairs)',json.dumps(data['interaction'],indent=2)]
 lines+=['','## Numerical checks',json.dumps(data['checks'],indent=2),'','## Sampling recipe',json.dumps(data['sampling'],indent=2),'','## Full source inputs, probe and local-pair evidence',json.dumps(data['studies'],indent=2),'','## Signed decomposition and contrast changes',json.dumps(data['comparisons'],indent=2),'','## Limits',*['- '+s for s in LIMITS]];(dest/'report.md').write_text('\n'.join(lines)+'\n')
 with (dest/'verification.csv').open('w',newline='') as stream:
  w=csv.writer(stream);w.writerow(['sampling_version','comparison','from_run_id','to_run_id','from_manifest_sha256','to_manifest_sha256','kind','probe_or_pair','upstream_referenced_change_m2_s2','local_anchor_change_m2_s2','anchor_upstream_change_m2_s2','closure_residual_m2_s2','local_pair_change_m2_s2'])
  hashes={s['run_id']:s['manifest_sha256'] for s in data['studies']}
  for c in data['comparisons']:
   prefix=[COMPACT,c['label'],c['from_run_id'],c['to_run_id'],hashes[c['from_run_id']],hashes[c['to_run_id']]]
   for p in c['probes']:w.writerow(prefix+['probe',p['name'],p['upstream_referenced_change_m2_s2'],p['local_anchor_change_m2_s2'],p['anchor_upstream_change_m2_s2'],p['closure_residual_m2_s2'],''])
   for p in c['local_pressure_pairs']:w.writerow(prefix+['local_pair',p['name'],'','','','',p['change_m2_s2']])
 manifest={'schema_version':1,'kind':'bracket_flow_reference','run_id':dest.name,'parent_design_id':str(parent),'created_at':datetime.now(timezone.utc).isoformat(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sampling_source_sha256':hashlib.sha256(Path(__file__).with_name('flow_sampling.py').read_bytes()).hexdigest(),'source_parent_manifest_sha256':record['manifest_sha256'],'sampling_version':COMPACT,'validation_status':status,'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}};(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));return dest

def run_study(root,parent,record,registry,include_fine_outer=False):
 from kcee.flow_sources import reusable
 from kcee.bracket_flow_run import run_bracket_flow
 sources=[];root=Path(root)
 recipes=[('medium','far','baseline'),('fine','far','baseline'),('medium','far',LOCAL_PROFILE),('fine','far',LOCAL_PROFILE),('medium','outer',LOCAL_PROFILE)]
 if include_fine_outer:recipes.append(('fine','outer',LOCAL_PROFILE))
 for mesh,domain,profile in recipes:
  source=reusable(root,parent,record,registry,mesh,domain,local_profile=profile)
  if source is None:
   if domain!='outer':raise ValueError('Run the Compact v1 wake/below refinement study first')
   dest=run_bracket_flow(root,parent,record,mesh,domain,4,COMPACT,profile);registry.register(dest);registry.verify(root,dest.name);_,digest=verify_directory(dest);source={'run_id':dest.name,'manifest_sha256':digest,'flow':json.loads((dest/'cfd.json').read_text())}
  sources.append(source)
 return save(root,parent,record,sources)
