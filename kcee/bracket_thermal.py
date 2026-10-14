"""Fixed steady conduction on a native-STL quadratic tetrahedral mesh.
Geometry mm; conductivity .015 W/(mm K) = 15 W/(m K); temperature Celsius.
"""
import hashlib,io,json,math,os,subprocess,zipfile
from pathlib import Path
from kcee.bracket_fea import mesh
from kcee.fea import SolverError,table

def surface(nodes,elements,temperatures):
    faces={};counts={}
    for element in elements:
        if len(element)!=10 or len(set(element))!=10:raise ValueError('Invalid quadratic tetrahedron')
        for indices in ((0,2,1,6,5,4),(0,1,3,4,8,7),(1,2,3,5,9,8),(2,0,3,6,7,9)):
            face=[element[i] for i in indices];key=tuple(sorted(face[:3]))
            counts[key]=counts.get(key,0)+1
            if counts[key]>2:raise ValueError('Non-manifold thermal mesh')
            faces[key]=None if key in faces else face
    triangles=[]
    for face in faces.values():
        if face is None:continue
        a,b,c,ab,bc,ca=face;triangles.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
    ids=sorted({node for triangle in triangles for node in triangle});lookup={node:index for index,node in enumerate(ids)}
    if not ids or any(node not in temperatures for node in ids):raise SolverError('Incomplete thermal surface')
    values=[temperatures[node] for node in ids]
    if not all(math.isfinite(value) for value in values):raise SolverError('Non-finite thermal field')
    return {'schema_version':1,'positions':[nodes[node] for node in ids],'temperatures_C':values,'triangles':[[lookup[node] for node in triangle] for triangle in triangles],'minimum_temperature_C':min(values),'maximum_temperature_C':max(values),'units':'mm, degrees Celsius','method':'Fine quadratic tetrahedron boundary; four linear display triangles per face'}

def solve_mesh(stl,directory,size,angle):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    nodes,elements,cold,_,summary=mesh(stl,directory,size,angle)
    hot=[node for node,(x,y,z) in nodes.items() if abs(x-60)<.05 and z<=3.55]
    if len(nodes)>50000 or len(hot)<10 or set(cold)&set(hot):raise SolverError('Thermal mesh/boundary budget violated')
    def node_set(name,ids):return ['*NSET,NSET='+name]+[','.join(map(str,ids[i:i+16])) for i in range(0,len(ids),16)]
    lines=['*NODE,NSET=NALL']+[str(node)+','+','.join(f'{v:.9E}' for v in point) for node,point in nodes.items()]+['*ELEMENT,TYPE=C3D10,ELSET=SOLID']+[str(index)+','+','.join(map(str,element)) for index,element in enumerate(elements,1)]
    lines+=node_set('COLD',cold)+node_set('HOT',hot)+['*MATERIAL,NAME=ILLUSTRATIVE','*CONDUCTIVITY','.015','*SOLID SECTION,ELSET=SOLID,MATERIAL=ILLUSTRATIVE','*INITIAL CONDITIONS,TYPE=TEMPERATURE','NALL,20','*STEP','*HEAT TRANSFER,STEADY STATE','1,1','*BOUNDARY','COLD,11,11,20','HOT,11,11,80','*NODE PRINT,NSET=NALL','NT,RFL','*NODE FILE','NT','*EL FILE','HFL','*END STEP']
    (directory/'thermal.inp').write_text('\n'.join(lines)+'\n')
    process=subprocess.run(['ccx','-i','thermal'],cwd=directory,capture_output=True,text=True,timeout=120,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
    (directory/'solver.log').write_text(process.stdout+'\n'+process.stderr)
    if process.returncode or '*ERROR' in process.stdout or 'Job finished' not in process.stdout:raise SolverError('Thermal solve failed')
    data=(directory/'thermal.dat').read_text();temperatures={int(row[0]):row[1] for row in table(data,'temperatures')};reactions={int(row[0]):row[1] for row in table(data,'heat generation')}
    if set(temperatures)!=set(nodes) or set(reactions)!=set(nodes):raise SolverError('Incomplete thermal nodal output')
    hot_heat=sum(reactions[node] for node in hot);cold_heat=sum(reactions[node] for node in cold)
    volume_mean=0.
    for e in elements:
        a,b,c,d=[nodes[node] for node in e[:4]];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[d[i]-a[i] for i in range(3)]
        volume=(u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0]))/6
        volume_mean+=volume*(-sum(temperatures[node] for node in e[:4])/20+sum(temperatures[node] for node in e[4:])/5)
    summary.update({'hot_nodes':len(hot),'cold_nodes':len(cold),'minimum_temperature_C':min(temperatures.values()),'maximum_temperature_C':max(temperatures.values()),'volume_mean_temperature_C':volume_mean/summary['volume_mm3'],'hot_reaction_heat_W':hot_heat,'cold_reaction_heat_W':cold_heat,'relative_heat_balance_error':abs(hot_heat+cold_heat)/max(abs(hot_heat),1e-12),'maximum_prescribed_temperature_error_C':max([abs(temperatures[node]-20) for node in cold]+[abs(temperatures[node]-80) for node in hot])})
    (directory/'temperature.csv').write_text('node,x_mm,y_mm,z_mm,temperature_C,reaction_heat_W\n'+'\n'.join(','.join(map(str,(node,*nodes[node],temperatures[node],reactions[node]))) for node in sorted(nodes))+'\n')
    (directory/'mesh-summary.json').write_text(json.dumps(summary,indent=2))
    (directory/'thermal-surface.json').write_text(json.dumps(surface(nodes,elements,temperatures)))
    return summary

def verify_bar(directory):
    from kcee.fea import deck
    directory=Path(directory);directory.mkdir()
    original,nodes,hot,cold,_=deck(8,2,1)
    prefix=original.split('*MATERIAL')[0].replace('*NODE\n','*NODE,NSET=NALL\n',1)
    text=prefix+'*MATERIAL,NAME=THERMAL\n*CONDUCTIVITY\n.015\n*SOLID SECTION,ELSET=SOLID,MATERIAL=THERMAL\n*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,20\n*STEP\n*HEAT TRANSFER,STEADY STATE\n1,1\n*BOUNDARY\nFIXED,11,11,20\nTIP,11,11,80\n*NODE PRINT,NSET=NALL\nNT,RFL\n*EL PRINT,ELSET=SOLID\nHFL\n*END STEP\n'
    (directory/'bar.inp').write_text(text)
    process=subprocess.run(['ccx','-i','bar'],cwd=directory,capture_output=True,text=True,timeout=30,env={**os.environ,'OMP_NUM_THREADS':'1'})
    (directory/'solver.log').write_text(process.stdout+'\n'+process.stderr)
    if process.returncode or '*ERROR' in process.stdout or 'Job finished' not in process.stdout:raise SolverError('Thermal bar verification solve failed')
    data=(directory/'bar.dat').read_text();temperatures={int(row[0]):row[1] for row in table(data,'temperatures')};reactions={int(row[0]):row[1] for row in table(data,'heat generation')}
    error=max(abs(temperatures[node]-(20+point[0])) for node,point in nodes.items());heat=sum(reactions[node] for node in hot);relative=abs(heat/.525-1)
    result={'geometry':'60 x 10 x 3.5 mm rectangular bar','element_type':'C3D20','analytical_temperature':'20 + x_mm degrees Celsius','analytical_heat_W':.525,'maximum_temperature_error_C':error,'computed_hot_heat_W':heat,'relative_heat_error':relative,'passed':error<1e-5 and relative<1e-5}
    (directory/'verification.json').write_text(json.dumps(result,indent=2))
    if not result['passed']:raise SolverError('Thermal bar verification checks failed')
    return result

def solve(stl,destination,expected_volume,angle):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    verification=verify_bar(destination/'solver-verification')
    rows=[solve_mesh(stl,destination/('mesh-'+str(size)),size,angle) for size in (2.5,1.8,1.5)]
    heat_change=abs(rows[-1]['hot_reaction_heat_W']/rows[-2]['hot_reaction_heat_W']-1);mean_change=abs(rows[-1]['volume_mean_temperature_C']-rows[-2]['volume_mean_temperature_C']);volume_error=abs(rows[-1]['volume_mm3']/expected_volume-1)
    checks={'solver_bar_verification':verification['passed'],'heat_balance':all(row['relative_heat_balance_error']<1e-6 for row in rows),'prescribed_temperatures':all(row['maximum_prescribed_temperature_error_C']<1e-6 for row in rows),'temperature_bounds':all(row['minimum_temperature_C']>=19.9 and row['maximum_temperature_C']<=80.1 for row in rows),'last_heat_flow_change':heat_change<.05,'last_mean_temperature_change':mean_change<.5,'source_volume_agreement':volume_error<.02}
    result={'solver_verification':verification,'kind':'bracket_thermal','source_stl_sha256':hashlib.sha256(Path(stl).read_bytes()).hexdigest(),'backend':'CalculiX 2.20 / Gmsh 4.8.4','element_type':'C3D10 thermal degree of freedom 11','conductivity_W_m_K':15,'conductivity_W_mm_K':.015,'boundary':'Rear upright nodes x≈0, z>3.5 mm at 20 °C; free-end nodes x≈60 mm at 80 °C; all remaining surfaces insulated','mesh_study':rows,'last_relative_heat_flow_change':heat_change,'last_mean_temperature_change_C':mean_change,'relative_source_volume_error':volume_error,'checks':checks,'tolerances':{'relative_heat_balance_error':1e-6,'prescribed_temperature_error_C':1e-6,'temperature_bounds_C':[19.9,80.1],'last_relative_heat_flow_change':.05,'last_mean_temperature_change_C':.5,'relative_source_volume_error':.02},'validation_status':'thermal_numerical_checks_passed_not_engineering_validated' if all(checks.values()) else 'thermal_numerical_checks_failed','adapter_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'meshing_source_sha256':hashlib.sha256(Path(__file__).with_name('bracket_fea.py').read_bytes()).hexdigest(),'solver_binary_sha256':hashlib.sha256(Path('/usr/bin/ccx').read_bytes()).hexdigest(),'limits':['Fixed illustrative conductivity and ideal temperature reservoirs, not realistic mounting/contact','Steady conduction only; no convection, radiation, heat generation, transient response or thermal expansion','Mesh checks do not establish local heat-flux convergence or engineering acceptance']}
    (destination/'thermal.json').write_text(json.dumps(result,indent=2))
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(destination))
    (destination/'thermal-artifacts.zip').write_bytes(output.getvalue())
    return result
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--stl',required=True);parser.add_argument('--output',required=True);parser.add_argument('--expected-volume',type=float,required=True);parser.add_argument('--angle',type=int,choices=(20,25),required=True);args=parser.parse_args();solve(args.stl,args.output,args.expected_volume,args.angle)
