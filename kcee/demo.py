"""Dependency-free pipeline; analytical screening is not structural validation."""
import argparse, hashlib, json, math, platform, subprocess, uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / 'examples/bracket/requirements.json'

def screen(req, thickness):
    g=req['geometry_mm']; b=g['width']; length=g['length']
    stress=6*req['load_N']*length/(b*thickness**2)
    displacement=4*req['load_N']*length**3/(req['youngs_modulus_MPa']*b*thickness**3)
    return {'stress_MPa':stress,'tip_deflection_mm':displacement,'factor_of_safety':req['yield_MPa']/stress}

def validate(req):
    g=req['geometry_mm']
    for value in list(g.values())+[req[k] for k in ('load_N','youngs_modulus_MPa','yield_MPa','density_kg_m3','minimum_factor_of_safety')]+[req['manufacturing']['minimum_thickness_mm']]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
            raise ValueError('All dimensional and physical inputs must be finite and positive')
    if g['thickness']>=min(g['length'],g['height']): raise ValueError('Thickness must be less than length and height')

def stl(g):
    # Extrude the concave L polygon in x/z; separate triangulated end faces.
    l,w,h,t=(g[k] for k in ('length','width','height','thickness'))
    polygon=[(0,0),(l,0),(l,t),(t,t),(t,h),(0,h)]
    verts=[(x,y,z) for y in (0,w) for x,z in polygon]
    face=[(0,1,3),(1,2,3),(0,3,5),(3,4,5)]
    triangles=list(face)+[tuple(i+6 for i in reversed(f)) for f in face]
    for i in range(6):
        j=(i+1)%6; triangles += [(i,i+6,j+6),(i,j+6,j)]
    lines=['solid bracket']
    for ids in triangles:
        a,b,c=[verts[i] for i in ids]
        u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
        n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        norm=math.sqrt(sum(x*x for x in n)); n=[x/norm for x in n]
        lines+=['facet normal '+' '.join(map(str,n)),'outer loop']
        lines += ['vertex '+' '.join(map(str,p)) for p in (a,b,c)]
        lines+=['endloop','endfacet']
    return '\n'.join(lines+['endsolid bracket'])+'\n'

def run(output, requirements=DEFAULT, geometry_backend="mesh", picogk_executable=None):
    if geometry_backend not in ("mesh","picogk"): raise ValueError("Unknown geometry backend")
    req=json.loads(Path(requirements).read_text()); validate(req)
    run_id=str(uuid.uuid4()); dest=Path(output)/run_id; dest.mkdir(parents=True,exist_ok=False)
    g=req['geometry_mm']; upper=min(g['length'],g['height'])
    candidates=[]
    t=req['manufacturing']['minimum_thickness_mm']
    while t<upper:
        result=screen(req,t)
        candidates.append({'thickness_mm':t,**result,'accepted':result['factor_of_safety']>=req['minimum_factor_of_safety']})
        t=round(t+0.5,6)
    viable=[x for x in candidates if x['accepted']]
    if not viable: raise ValueError('No feasible thickness in search range')
    best=min(viable,key=lambda x:x['thickness_mm']); geometry={**g,'thickness':best['thickness_mm']}
    mass=g['width']*best['thickness_mm']*(g['length']+g['height']-best['thickness_mm'])*1e-9*req['density_kg_m3']
    result={'validation_status':'unvalidated_analytical_screening','geometry_backend':'deterministic_mesh_fallback','structural_backend':'Euler-Bernoulli cantilever approximation','selected':best,'mass_kg':mass,'candidates':candidates,'assumptions':['SI loads, geometry in mm, MPa=N/mm^2','Perfectly fixed root, end point load, linear elasticity','No holes, fillets, stress concentrations, bolt contact, buckling or fatigue','Thermal, CFD and Cantera not applicable to this demo; not executed']}
    (dest/'requirements.json').write_text(json.dumps(req,indent=2))
    if geometry_backend=='picogk':
        from kcee.picogk import generate, GeometryError
        try:
            metadata=generate(dest,geometry,req.get('geometry_options'),picogk_executable)
        except GeometryError as exc:
            (dest/'failure.json').write_text(json.dumps({'run_id':run_id,'stage':'geometry','status':'failed','error':str(exc)},indent=2))
            raise
        result['geometry_backend']='PicoGK '+metadata['package_version']
        result['geometry']=metadata
        result['mass_kg']=metadata['volume_mm3']*1e-9*req['density_kg_m3']
        result['assumptions'].append('PicoGK holes/fillet geometry is not represented in the analytical stress/deflection model; mass uses voxel volume')
    else:
        (dest/'bracket.stl').write_text(stl(geometry))
    (dest/'result.json').write_text(json.dumps(result,indent=2))
    (dest/'voice-summary.json').write_text(json.dumps({'level':'RESULT','text':'Bracket screening complete. Design remains unvalidated. Selected thickness '+str(best['thickness_mm'])+' millimeters.','delivery':'queued_artifact_only; Kokoro not connected'},indent=2))
    (dest/'report.md').write_text('# Bracket screening\n\nUNVALIDATED: analytical approximation only.\n\nThickness: '+str(best['thickness_mm'])+' mm\n\n'+json.dumps(best,indent=2)+'\n\nAssumptions:\n'+ '\n'.join('- '+x for x in result['assumptions']))
    try: commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],stderr=subprocess.DEVNULL,text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError): commit=None
    source=Path(__file__)
    manifest={'schema_version':1,'run_id':run_id,'parent_design_id':None,'created_at':datetime.now(timezone.utc).isoformat(),'software_commit':commit,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'runtime':platform.python_version(),'requirements_source':str(Path(requirements).resolve()),'validation_status':result['validation_status'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir())}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)); return dest

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='runs'); parser.add_argument('--requirements',default=str(DEFAULT)); parser.add_argument('--geometry-backend',choices=['mesh','picogk'],default='mesh'); args=parser.parse_args()
    print(run(args.output,args.requirements,args.geometry_backend))
