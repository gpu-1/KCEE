"""STL-derived bracket volume mesh and explicit idealized mounting/load study."""
import hashlib,io,json,math,os,subprocess,zipfile
from pathlib import Path
import gmsh
from kcee.fea import SolverError,table

def mesh(stl,directory,size):
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.logger.start()
    try:
        gmsh.merge(str(stl));gmsh.model.mesh.classifySurfaces(math.pi/9,True,True,math.pi);gmsh.model.mesh.createGeometry()
        surfaces=[tag for dim,tag in gmsh.model.getEntities(2)]
        shell=gmsh.model.geo.addSurfaceLoop(surfaces);gmsh.model.geo.addVolume([shell]);gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin',size);gmsh.option.setNumber('Mesh.MeshSizeMax',size)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0);gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
        gmsh.option.setNumber('Mesh.Algorithm3D',1);gmsh.option.setNumber('Mesh.SecondOrderLinear',1)
        gmsh.model.mesh.generate(3);gmsh.model.mesh.setOrder(2)
        tags,coordinates,_=gmsh.model.mesh.getNodes();nodes={int(tag):tuple(map(float,coordinates[i*3:i*3+3])) for i,tag in enumerate(tags)}
        types,element_ids,connectivity=gmsh.model.mesh.getElements(3)
        if len(types)!=1 or types[0]!=11:raise SolverError('Expected quadratic tetrahedral volume elements')
        ids=list(map(int,element_ids[0]));flat=list(map(int,connectivity[0]));elements=[flat[i:i+10] for i in range(0,len(flat),10)]
        # Gmsh edge order: 12,23,31,14,34,24. CalculiX: 12,23,31,14,24,34.
        elements=[e[:8]+[e[9],e[8]] for e in elements]
        midpoint_error=0.0
        for element in elements:
            for index,(a,b) in enumerate(((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))):
                expected=tuple((nodes[element[a]][j]+nodes[element[b]][j])/2 for j in range(3))
                actual=nodes[element[4+index]]
                midpoint_error=max(midpoint_error,math.sqrt(sum((actual[j]-expected[j])**2 for j in range(3))))
        if midpoint_error>1e-6:raise SolverError('Quadratic tetrahedron node ordering mismatch')
        fixed=[tag for tag,(x,y,z) in nodes.items() if abs(x)<.05 and z>3.5]
        if len(fixed)<20:raise SolverError('Rear mounting face not resolved')
        types,surface_ids,faces=gmsh.model.mesh.getElements(2);index=list(types).index(9);raw=list(map(int,faces[index]));loads={};area_total=0
        for i in range(0,len(raw),6):
            face=raw[i:i+6];a,b,c=[nodes[n] for n in face[:3]]
            if min(p[0] for p in (a,b,c))<54 or max(abs(p[2]-3.5) for p in (a,b,c))>.05:continue
            if sum(p[0] for p in (a,b,c))/3<55:continue
            u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)];cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            area=math.sqrt(sum(x*x for x in cross))/2;area_total+=area
            for node in face[3:]:loads[node]=loads.get(node,0)+area/3
        if area_total<75:raise SolverError('Free-end load patch not resolved')
        loads={node:-100*weight/area_total for node,weight in loads.items()}
        minimum=math.inf;volume=0
        for e in elements:
            a,b,c,d=[nodes[n] for n in e[:4]]
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[d[i]-a[i] for i in range(3)]
            determinant=u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0])
            if determinant<=0:raise SolverError('Non-positive tetrahedron volume')
            minimum=min(minimum,determinant/6);volume+=determinant/6
        gmsh.write(str(directory/'volume.msh'))
        (directory/'gmsh.log').write_text('\n'.join(gmsh.logger.get()))
        return nodes,elements,fixed,loads,{'maximum_midside_mapping_error_mm':midpoint_error,'mesher_version':gmsh.option.getString('General.Version'),'target_size_mm':size,'nodes':len(nodes),'elements':len(elements),'volume_mm3':volume,'minimum_tetrahedron_volume_mm3':minimum,'load_patch_area_mm2':area_total,'fixed_nodes':len(fixed)}
    finally:
        (directory/'gmsh.log').write_text('\n'.join(gmsh.logger.get()))
        gmsh.logger.stop();gmsh.finalize()

def solve(stl,destination,expected_volume=None):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True);study=[]
    for size in (2.5,1.8,1.5):
        directory=destination/('mesh-'+str(size));directory.mkdir()
        nodes,elements,fixed,loads,summary=mesh(stl,directory,size)
        if len(nodes)>50000:raise SolverError('Mesh exceeds demo node budget')
        def set_lines(name,ids):return ['*NSET,NSET='+name]+[','.join(map(str,ids[i:i+16])) for i in range(0,len(ids),16)]
        lines=['*NODE']+[str(n)+','+','.join(f'{value:.9E}' for value in p) for n,p in nodes.items()]+['*ELEMENT,TYPE=C3D10,ELSET=SOLID']+[str(i)+','+','.join(map(str,e)) for i,e in enumerate(elements,1)]
        lines+=set_lines('FIXED',fixed)+set_lines('LOADED',list(loads))+['*MATERIAL,NAME=ALUMINUM','*ELASTIC','69000,0.33','*SOLID SECTION,ELSET=SOLID,MATERIAL=ALUMINUM','*BOUNDARY','FIXED,1,3','*STEP','*STATIC','*CLOAD']
        lines += [f'{n},3,{f:.9E}' for n,f in loads.items()]+['*NODE PRINT,NSET=LOADED','U','*NODE PRINT,NSET=FIXED','RF','*EL PRINT,ELSET=SOLID','S','*NODE FILE','U','*EL FILE','S','*END STEP']
        (directory/'bracket.inp').write_text('\n'.join(lines)+'\n')
        completed=subprocess.run(['ccx','-i','bracket'],cwd=directory,capture_output=True,text=True,timeout=120,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
        (directory/'solver.log').write_text(completed.stdout+'\n'+completed.stderr)
        if completed.returncode!=0 or '*ERROR' in completed.stdout or 'Job finished' not in completed.stdout:raise SolverError('Bracket solve failed')
        data=(directory/'bracket.dat').read_text();displacements={int(row[0]):row[3] for row in table(data,'displacements')}
        reaction=sum(row[3] for row in table(data,'forces'));stress=[]
        for row in table(data,'stresses'):
            sx,sy,sz,txy,txz,tyz=row[2:8];stress.append(math.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(txy*txy+txz*txz+tyz*tyz)))
        summary.update({'tip_deflection_mm':abs(sum(displacements[n]*f for n,f in loads.items())/100),'reaction_z_N':reaction,'maximum_von_mises_MPa':max(stress)})
        study.append(summary)
        (directory/'mesh-summary.json').write_text(json.dumps(summary,indent=2))
    change=abs(study[-1]['tip_deflection_mm']/study[-2]['tip_deflection_mm']-1)
    patch_change=abs(study[-1]['load_patch_area_mm2']/study[-2]['load_patch_area_mm2']-1)
    volume_error=abs(study[-1]['volume_mm3']/expected_volume-1) if expected_volume else None
    checks={'load_patch_refinement':patch_change<.05,'source_volume_agreement':volume_error is not None and volume_error<.02,'force_balance':all(abs(item['reaction_z_N']-100)<.1 for item in study),'displacement_refinement':change<.05}
    result={'schema_version':1,'backend':'CalculiX','version':'2.20','mesher_version':study[-1]['mesher_version'],'mesher_api_version':gmsh.__version__,'element_type':'C3D10','geometry':'native_PicoGK_STL','source_stl_sha256':hashlib.sha256(Path(stl).read_bytes()).hexdigest(),'mesh_study':study,'last_mesh_displacement_change':change,'last_load_patch_area_change':patch_change,'relative_source_volume_error':volume_error,'surface_classification_angle_degrees':20,'adapter_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'solver_binary_sha256':hashlib.sha256(Path('/usr/bin/ccx').read_bytes()).hexdigest(),'checks':checks,'validation_status':'numerical_checks_passed_not_engineering_validated' if all(checks.values()) else 'numerical_checks_failed','boundary':'All translations fixed on rear upright face x≈0, z>3.5 mm; ideal clamp, not bolt contact','load':'100 N downward distributed over top free-end strip x>=55 mm using consistent quadratic-face weights','material':{'youngs_modulus_MPa':69000,'poisson_ratio':.33,'source':'Illustrative aluminum properties'},'stress_note':'Peak stresses are not accepted as converged allowables; mounting and load-patch edges can be singular.'}
    (destination/'fea.json').write_text(json.dumps(result,indent=2))
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(destination.rglob('*')):
            if path.is_file():zipped.write(path,path.relative_to(destination))
    return result,archive.getvalue()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--stl',required=True);parser.add_argument('--output',required=True);parser.add_argument('--expected-volume',type=float,required=True);args=parser.parse_args()
    result,archive=solve(args.stl,args.output,args.expected_volume)
    (Path(args.output)/'fea-artifacts.zip').write_bytes(archive)
