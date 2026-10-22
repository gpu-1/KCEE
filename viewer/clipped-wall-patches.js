import {faceMap} from './wall-fields-view.js';
import {PATCHES} from './wall-patches.js';
export const METHOD='native-wall-clipped-patches-v1';
// Clip a convex display triangle to an axis-aligned square in its wall plane.
export function clipSquare(points,axes,centre,half){
 let polygon=points.map(p=>[...p]);
 for(const axis of axes)for(const sign of [-1,1]){
  const bound=centre[axis]+sign*half,inside=p=>sign*(p[axis]-bound)<=0,next=[];
  for(let i=0;i<polygon.length;i++){
   const a=polygon[i],b=polygon[(i+1)%polygon.length],ia=inside(a),ib=inside(b);
   if(ia)next.push(a);
   if(ia!==ib){const t=(bound-a[axis])/(b[axis]-a[axis]);next.push(a.map((v,j)=>v+t*(b[j]-v)));}
  }
  polygon=next;
 }
 return polygon;
}
export function projectedMeasure(points,axes){
 let area=0,moment=[0,0,0];const [u,v]=axes;
 for(let i=1;i+1<points.length;i++){
  const [a,b,c]=[points[0],points[i],points[i+1]],w=Math.abs((b[u]-a[u])*(c[v]-a[v])-(b[v]-a[v])*(c[u]-a[u]))/2;
  area+=w;moment=moment.map((x,j)=>x+w*(a[j]+b[j]+c[j])/3);
 }
 return {area,moment};
}
export function clippedWallPatches(data){
 const map=faceMap(data),s=data.surface,points=s.positions_mm,half=.002,planeTolerance=.00005;
 if(!Array.isArray(points)||!points.every(p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite))||s.triangles.length!==s.triangle_source_faces.length||!s.triangles.every(t=>Array.isArray(t)&&t.length===3&&t.every(i=>Number.isInteger(i)&&i>=0&&i<points.length)))throw Error('Invalid clipping surface geometry');
 const vertices=points.map(p=>p.map(v=>v/1000));
 const patches=PATCHES.map(p=>{
  const normalAxis=p.normal.findIndex(v=>v!==0),axes=[0,1,2].filter(i=>i!==normalAxis),eligible=new Map();
  for(const f of map.values()){
   const norm=Math.hypot(...f.area_vector_m2),alignment=f.area_vector_m2.reduce((a,v,i)=>a+v*p.normal[i],0)/norm;
   if(alignment>=.95&&Math.abs(f.centre_m[normalAxis]-p.centre_m[normalAxis])<=planeTolerance)eligible.set(f.face,{row:f,full:0,clipped:0,moment:[0,0,0]});
  }
  s.triangles.forEach((t,i)=>{const record=eligible.get(s.triangle_source_faces[i]);if(!record)return;const triangle=t.map(j=>vertices[j]);
   const full=projectedMeasure(triangle,axes),clipped=projectedMeasure(clipSquare(triangle,axes,p.centre_m,half),axes);
   if(clipped.area>0&&triangle.some(v=>Math.abs(v[normalAxis]-p.centre_m[normalAxis])>planeTolerance))throw Error('Selected wall polygon leaves clipping plane tolerance');
   record.full+=full.area;record.clipped+=clipped.area;record.moment=record.moment.map((v,j)=>v+clipped.moment[j]);
  });
  const selected=[...eligible.values()].filter(r=>r.clipped>0).map(r=>{if(!(r.full>0)||r.clipped>r.full*(1+1e-10))throw Error('Invalid clipped native face fraction');return {...r,fraction:r.clipped/r.full,weight:r.row.area_m2*(r.clipped/r.full),centre:r.moment.map(v=>v/r.clipped)};});
  if(!selected.length)return {...p,available:false,reason:'No aligned planar wall surface overlaps the fixed square'};
  const sum=get=>selected.reduce((a,r)=>a+get(r),0),projected=sum(r=>r.clipped),area=sum(r=>r.weight),average=get=>sum(r=>r.weight*get(r))/area,centroid=[0,1,2].map(i=>average(r=>r.centre[i])),nominal=(2*half)**2;
  const result={...p,available:true,coverage_complete:Math.abs(projected/nominal-1)<=.001,faces:selected.length,projected_area_m2:projected,nominal_square_area_m2:nominal,projected_coverage_fraction:projected/nominal,native_weighted_area_m2:area,sampled_centre_m:centroid,centre_offset_m:Math.hypot(...centroid.map((v,i)=>v-p.centre_m[i])),mean_pressure_Pa:average(r=>r.row.pressure_Pa),mean_viscous_traction_Pa:[0,1,2].map(i=>average(r=>r.row.viscous_traction_Pa[i])),mean_total_traction_Pa:[0,1,2].map(i=>average(r=>r.row.total_traction_Pa[i])),mean_viscous_magnitude_Pa:average(r=>Math.hypot(...r.row.viscous_traction_Pa)),mean_total_magnitude_Pa:average(r=>Math.hypot(...r.row.total_traction_Pa)),face_weights:selected.map(r=>({face:r.row.face,fraction:r.fraction,native_area_m2:r.row.area_m2,projected_overlap_m2:r.clipped,weight_m2:r.weight}))};
  if(![projected,area,...centroid,result.mean_pressure_Pa,...result.mean_viscous_traction_Pa,...result.mean_total_traction_Pa,result.mean_viscous_magnitude_Pa,result.mean_total_magnitude_Pa].every(Number.isFinite)||area<=0)throw Error('Nonfinite clipped wall patch result');return result;
 });
 return {schema:METHOD,half_width_m:half,plane_tolerance_m:planeTolerance,normal_alignment_min:.95,patches,limits:'Common 4 × 4 mm squares on the base upper and upright front/rear planes. Triangle polygons are clipped in the wall plane; fractions are aggregated per native parent face and multiply its native area. Native parent values remain piecewise constant. Projected coverage within 0.1% of the nominal square is a footprint check, not a solver-accuracy gate. Incomplete coverage is flagged. Local means still depend on the saved solution and face quadrature; no point interpolation, mesh-convergence order, uncertainty bound or engineering acceptance is inferred. Square results are a separate footprint from the earlier 2 mm radius face-centre samples.'};
}
