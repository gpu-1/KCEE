const finite3=v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite);
export function faceMap(data){
 const f=data?.wall_fields;if(data.schema!=='native-wall-fields-v1'||f?.method!=='native-wall-fields-v1'||f.units!=='Pa'||!Array.isArray(f.faces)||f.faces.length!==data.surface.wall_faces)throw Error('Invalid native wall fields');
 const map=new Map();
 for(const r of f.faces){if(!Number.isInteger(r.face)||r.face<0||map.has(r.face)||!Number.isFinite(r.pressure_Pa)||!Number.isFinite(r.area_m2)||r.area_m2<=0||!['centre_m','area_vector_m2','pressure_force_N','viscous_force_N','total_force_N','viscous_traction_Pa','total_traction_Pa'].every(k=>finite3(r[k])))throw Error('Invalid native wall face values');map.set(r.face,r);}
 if(new Set(data.surface.triangle_source_faces).size!==map.size||data.surface.triangle_source_faces.some(i=>!map.has(i)))throw Error('Wall field identities differ from geometry');return map;
}
export function fieldValue(face,mode,axis='magnitude'){
 if(mode==='pressure')return face.pressure_Pa;if(!['viscous','total'].includes(mode)||!['magnitude','0','1','2'].includes(String(axis)))throw Error('Unsupported wall field');const v=face[mode+'_traction_Pa'];return axis==='magnitude'?Math.hypot(...v):v[Number(axis)];
}
const linear=c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4;
export function fieldColors(geometry,data,mode,axis='magnitude',selected=-1){
 const map=faceMap(data);if(mode==='regions')return {...geometry,unlit:false,faceMap:map,legend:null};
 const values=[...map.values()].map(r=>fieldValue(r,mode,axis)),min=values.reduce((a,b)=>Math.min(a,b),Infinity),max=values.reduce((a,b)=>Math.max(a,b),-Infinity),signed=mode==='pressure'||axis!=='magnitude',span=signed?Math.max(Math.abs(min),Math.abs(max)):max,lo=signed?-span:0,hi=span;
 const colors=[];data.surface.triangle_source_faces.forEach((id,i)=>{const v=fieldValue(map.get(id),mode,axis),t=hi===lo?(signed?.5:0):(v-lo)/(hi-lo),rgb=t<.5?[0,2*t,1]:[2*t-1,2-2*t,2-2*t],dim=selected>=0&&data.surface.triangle_regions[i]!==selected;
  const color=dim?[.025,.04,.055]:rgb.map(linear);for(let j=0;j<3;j++)colors.push(...color);
 });
 return {...geometry,colors,unlit:true,faceMap:map,legend:{min:lo,max:hi,actualMin:min,actualMax:max,signed,label:mode==='pressure'?'Pressure relative to outlet':(mode==='viscous'?'Full viscous traction':'Total traction')+' '+(axis==='magnitude'?'magnitude':'xyz'[Number(axis)]+' component'),units:'Pa'}};
}
export function faceDescription(data,index){
 if(!Number.isInteger(index)||index<0||index>=data.surface.triangles.length)throw Error('Invalid selected triangle');const face=data.surface.triangle_source_faces[index],r=faceMap(data).get(face),region=data.regions[data.surface.triangle_regions[index]],vector=v=>v.map(x=>x.toExponential(5)).join(', ');
 return 'Native face '+face+' · '+region+' · centre ('+vector(r.centre_m.map(x=>x*1000))+') mm · area '+r.area_m2.toExponential(5)+' m². Pressure '+r.pressure_Pa.toExponential(5)+' Pa relative to outlet. Full viscous traction (x,y,z): '+vector(r.viscous_traction_Pa)+' Pa. Total traction: '+vector(r.total_traction_Pa)+' Pa. Pressure force: '+vector(r.pressure_force_N)+' N. Viscous force: '+vector(r.viscous_force_N)+' N. Total force: '+vector(r.total_force_N)+' N. Parent face values; display triangles share this face value.';
}
