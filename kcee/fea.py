"""CalculiX quadratic-solid cantilever benchmark; never validates a bracket."""
import hashlib,io,json,math,os,re,subprocess,tempfile,zipfile,platform,shutil
from pathlib import Path

class SolverError(RuntimeError):pass

def deck(nx,ny,nz,L=60.,W=10.,T=3.5,F=10.,E=69000.,nu=.33):
    nodes={};coordinates={};elements=[]
    # C3D20 corner and edge-node ordering, using integer half-grid coordinates.
    offsets=[(0,0,0),(2,0,0),(2,2,0),(0,2,0),(0,0,2),(2,0,2),(2,2,2),(0,2,2),(1,0,0),(2,1,0),(1,2,0),(0,1,0),(1,0,2),(2,1,2),(1,2,2),(0,1,2),(0,0,1),(2,0,1),(2,2,1),(0,2,1)]
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                ids=[]
                for a,b,c in offsets:
                    key=(ix*2+a,iy*2+b,iz*2+c)
                    if key not in nodes:
                        node=len(nodes)+1;nodes[key]=node;coordinates[node]=(key[0]*L/(2*nx),key[1]*W/(2*ny),key[2]*T/(2*nz))
                    ids.append(nodes[key])
                elements.append(ids)
    fixed=[node for key,node in nodes.items() if key[0]==0]
    tip=[node for key,node in nodes.items() if key[0]==2*nx]
    # Uniform end-face traction: consistent quadratic face nodal loads.
    loads={node:0. for node in tip}
    face=[(0,0),(2,0),(2,2),(0,2),(1,0),(2,1),(1,2),(0,1)]
    for iy in range(ny):
        for iz in range(nz):
            for index,(b,c) in enumerate(face):loads[nodes[(2*nx,iy*2+b,iz*2+c)]]+=-F/(ny*nz)*(-1/12 if index<4 else 1/3)
    lines=['*NODE']+[f'{node},'+','.join(map(str,xyz)) for node,xyz in coordinates.items()]+['*ELEMENT,TYPE=C3D20,ELSET=SOLID']
    for index,ids in enumerate(elements,1):lines += [str(index)+','+','.join(map(str,ids[:15]))+',',','.join(map(str,ids[15:]))]
    lines+=['*NSET,NSET=FIXED']+[','.join(map(str,fixed[i:i+16])) for i in range(0,len(fixed),16)]+['*NSET,NSET=TIP']+[','.join(map(str,tip[i:i+16])) for i in range(0,len(tip),16)]+['*MATERIAL,NAME=ALUMINUM','*ELASTIC',f'{E},{nu}','*SOLID SECTION,ELSET=SOLID,MATERIAL=ALUMINUM','*BOUNDARY','FIXED,1,3','*STEP','*STATIC','*CLOAD']
    lines += [f'{node},3,{force}' for node,force in loads.items() if force]
    lines+=['*NODE PRINT,NSET=TIP','U','*NODE PRINT,NSET=FIXED','RF','*EL PRINT,ELSET=SOLID','S','*NODE FILE','U','*EL FILE','S','*END STEP']
    return '\n'.join(lines)+'\n',coordinates,tip,fixed,loads

def table(text,heading):
    records=[];active=False
    for line in text.splitlines():
        if heading in line.lower():active=True;continue
        if active:
            parts=line.split()
            if parts and parts[0].isdigit():
                try:records.append([float(x.replace('D','E')) for x in parts])
                except ValueError:pass
            elif records:break
    if not records:raise SolverError('Missing solver output: '+heading)
    return records

def benchmark(destination,ccx='ccx'):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    results=[]
    for nx,ny,nz in ((8,2,1),(16,4,2),(24,6,3)):
        directory=destination/f'mesh-{nx}';directory.mkdir()
        text,coords,tip,fixed,loads=deck(nx,ny,nz);(directory/'beam.inp').write_text(text)
        try:
            completed=subprocess.run([ccx,'-i','beam'],cwd=directory,capture_output=True,text=True,timeout=90,check=True,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
        except (OSError,subprocess.SubprocessError) as exc:raise SolverError('CalculiX execution failed') from exc
        (directory/'solver.log').write_text(completed.stdout+'\n'+completed.stderr)
        if '*ERROR' in completed.stdout or 'Job finished' not in completed.stdout:raise SolverError('CalculiX did not complete successfully')
        data=(directory/'beam.dat').read_text();u=table(data,'displacements');reaction=table(data,'forces');stress=table(data,'stresses')
        displacements={int(row[0]):row[3] for row in u}
        if set(displacements)!=set(tip):raise SolverError('Incomplete tip displacements')
        # Work-conjugate displacement under uniform traction, rather than one corner.
        deflection=sum(displacements[node]*force for node,force in loads.items())/-10.
        reaction_z=sum(row[3] for row in reaction)
        vm=[]
        for row in stress:
            sx,sy,sz,txy,txz,tyz=row[2:8]
            vm.append(math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(txy*txy+txz*txz+tyz*tyz)))
        results.append({'elements':nx*ny*nz,'nodes':len(coords),'mesh':[nx,ny,nz],'tip_deflection_mm':abs(deflection),'reaction_z_N':reaction_z,'maximum_von_mises_MPa':max(vm)})
    reference=4*10*60**3/(69000*10*3.5**3);fine=results[-1]
    relative=abs(fine['tip_deflection_mm']/reference-1);change=abs(fine['tip_deflection_mm']/results[-2]['tip_deflection_mm']-1)
    checks={'analytical_displacement_error_under_5_percent':relative<.05,'last_mesh_displacement_change_under_2_percent':change<.02,'reaction_balance_under_0_1_percent':all(abs(x['reaction_z_N']-10)<.01 for x in results)}
    if not all(checks.values()):raise SolverError('Cantilever benchmark acceptance checks failed: '+json.dumps(checks))
    info=subprocess.run([ccx,'-v'],capture_output=True,text=True)
    match=re.search(r'Version\s+([0-9.]+)',info.stdout,re.I)
    if not match:raise SolverError('Unable to identify CalculiX version')
    version=match.group(1)
    result={'schema_version':1,'backend':'CalculiX','version':version,'binary_sha256':hashlib.sha256(Path(shutil.which(ccx)).read_bytes()).hexdigest(),'adapter_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'architecture':platform.machine(),'geometry_mm':{'length':60,'width':10,'thickness':3.5},'element_type':'C3D20','geometry':'rectangular_cantilever_not_bracket','units':{'length':'mm','stress':'MPa','force':'N'},'material':{'youngs_modulus_MPa':69000,'poisson_ratio':.33,'source':'Illustrative benchmark data'},'load':'10 N downward, uniformly distributed at free end','boundary':'All translations fixed at x=0','analytical_tip_deflection_mm':reference,'mesh_study':results,'relative_displacement_error':relative,'last_mesh_displacement_change':change,'checks':checks,'validation_status':'benchmark_verified_only','stress_note':'Root stresses are affected by the fully fixed boundary; peak stress is not a converged bracket allowable.'}
    (destination/'fea.json').write_text(json.dumps(result,indent=2))
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(destination.rglob('*')):
            if path.is_file():zipped.write(path,path.relative_to(destination))
    return result,archive.getvalue()
