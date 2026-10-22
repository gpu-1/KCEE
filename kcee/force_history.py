"""Fixed native load histories and explicit iterative settling diagnostics."""
import json,math
from pathlib import Path
from kcee.flow_forces import norm,sub
PROFILE='wall-bore-history-v1'
FINE_PROFILE='wall-bore-history-fine-v2'
HOTSPOT_PROFILE='wall-hotspot-history-v1'
HISTORY_PROFILES=(PROFILE,FINE_PROFILE,HOTSPOT_PROFILE)
ITERATIONS=3000
CELLS={'coarse':[28,21,23],'medium':[35,27,29],'fine':[44,33,37]}
SCOPES=('dictionary::digest only; LD_PRELOAD only for native postprocessing','dictionary::digest only; LD_PRELOAD restricted to fixed native CFD commands')
def functions():
 return '\nfunctions {\n solverLoads {type forces; libs ("libforces.so"); patches (bracket); rho rhoInf; rhoInf 1; pRef 0; CofR (0 0 0); log false; writeControl timeStep; writeInterval 1;}\n}\n'
def postprocess_control(raw):
 suffix=functions().encode()
 return raw[:-len(suffix)] if raw.endswith(suffix) else raw

def parse(raw,iterations):
 from kcee.native_forces import native_vectors
 lines=[s.strip() for s in raw.decode().splitlines() if s.strip() and not s.lstrip().startswith('#')]
 if len(lines)!=iterations:raise ValueError('Incomplete native load history')
 return [native_vectors(line,i+1) for i,line in enumerate(lines)]
def summarize(forces,moments):
 if len(forces)!=len(moments) or len(forces)<400:raise ValueError('Insufficient matching force/moment history')
 rows=[{'iteration':i+1,**{component+'_'+quantity:series[i][component] for quantity,series in [('force_N',forces),('moment_N_m',moments)] for component in ('pressure','viscous','total')}} for i in range(len(forces))]
 window=100;stats={};checks={}
 for key in rows[0]:
  if key=='iteration':continue
  previous=[r[key] for r in rows[-2*window:-window]];last=[r[key] for r in rows[-window:]]
  mean=lambda a:[math.fsum(v[k] for v in a)/len(a) for k in range(3)]
  a,b=mean(previous),mean(last);floor=6e-8*(.06 if 'moment' in key else 1);scale=max(norm(b),floor)
  change=norm(sub(b,a))/scale;spread=max(norm(sub(v,b)) for v in last)/scale
  stats[key]={'previous_window_mean':a,'last_window_mean':b,'normalization':scale,'relative_window_mean_change':change,'relative_max_deviation_from_last_mean':spread}
  checks[key]=change<=.001 and spread<=.002
 return {'method':'native-load-history-v1','iterations':len(rows),'window_iterations':window,'tolerances':{'relative_window_mean_change':.001,'relative_max_deviation_from_last_mean':.002},'normalization':'max(norm(last-window component-vector mean), rho*U^2*Aref/2); moments additionally use 0.06 m','statistics':stats,'checks':checks,'iterative_settling':'criteria_met' if all(checks.values()) else 'not_established','series':rows,'limits':['These window checks assess recorded iterative changes, not residual error bounds, physical validation or mesh convergence.','Pressure, viscous and total force/moment vectors are checked separately so cancellation cannot hide component drift.']}
def evaluate(root):
 from kcee.native_forces import validate_runtime
 root=Path(root);runtime=json.loads((root/'runtime.json').read_text());meta=validate_runtime(runtime['force_history_runtime'])
 if meta['simpleFoam_sha256']!=runtime['binaries_sha256']['simpleFoam'] or meta['package']!=runtime['package']:raise ValueError('History solver fingerprint differs from source runtime')
 if runtime.get('solver_overlay_scope')!='dictionary::digest only; fixed force-history simpleFoam invocation':raise ValueError('Missing solver overlay scope')
 files=[]
 for n in ('force.dat','moment.dat'):
  paths=list((root/'postProcessing/solverLoads').glob('*/'+n))
  if len(paths)!=1:raise ValueError('Missing/ambiguous native solver history')
  files.append(parse(paths[0].read_bytes(),ITERATIONS))
 result=summarize(*files);result['runtime']=runtime['force_history_runtime'];return result

def mesh_comparison(rows):
 if len(rows)!=3:raise ValueError('Three history meshes are required')
 changes=[]
 for a,b in zip(rows,rows[1:]):
  d={}
  for key in ('pressure_force_N','viscous_force_N','total_force_N','pressure_moment_N_m','viscous_moment_N_m','total_moment_N_m'):
   x,y=a['loads'][key],b['loads'][key];delta=sub(y,x)
   d[key]={'signed_change':delta,'relative_change_to_finer_norm':norm(delta)/norm(y) if norm(y)>1e-30 else None}
  changes.append({'from_run_id':a['run_id'],'to_run_id':b['run_id'],'changes':d})
 return {'method':'three-mesh-component-sensitivity-v1','adjacent_mesh_changes':changes,'iterative_settling':all(r['force_history']['iterative_settling']=='criteria_met' for r in rows),'mesh_convergence':'not_established','reason':'Three locally refined, partially layered meshes are not a uniform refinement sequence; no observed-order or Richardson/GCI error estimate is inferred.'}
