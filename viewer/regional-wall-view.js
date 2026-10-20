export const REGION_COLORS=['#e5b56b','#e47e82','#80b6ed','#b398ec','#ed91cc','#77cfb8','#a8ce73'];
let generation=0,download=null;
export function wallGeometry(data,selected=-1){
 const s=data?.surface;if(data?.schema!=='native-regional-wall-view-v1'||s?.units!=='mm'||!Number.isInteger(selected)||selected< -1||selected>6||!s.positions_mm?.length||s.positions_mm.length>300000||!s.triangles?.length||s.triangles.length>250000||s.triangle_regions?.length!==s.triangles.length||s.triangle_source_faces?.length!==s.triangles.length)throw Error('Invalid regional wall geometry');
 if(!s.positions_mm.every(p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite)))throw Error('Invalid regional wall positions');
 const positions=[],colors=[],faceRegions=new Map();
 s.triangles.forEach((t,i)=>{const r=s.triangle_regions[i],face=s.triangle_source_faces[i];if(!Array.isArray(t)||t.length!==3||!t.every(v=>Number.isInteger(v)&&v>=0&&v<s.positions_mm.length)||!Number.isInteger(r)||r<0||r>6||!Number.isInteger(face)||face<0||(faceRegions.has(face)&&faceRegions.get(face)!==r))throw Error('Invalid regional wall addressing');faceRegions.set(face,r);
  const hex=selected<0||r===selected?REGION_COLORS[r]:'#344653',rgb=[1,3,5].map(j=>parseInt(hex.slice(j,j+2),16)/255);for(const v of t){positions.push(...s.positions_mm[v]);colors.push(...rgb);}
 });
 const counts=Array(7).fill(0);for(const r of faceRegions.values())counts[r]++;
 if(faceRegions.size!==s.wall_faces||counts.some((n,i)=>n!==s.region_face_counts[i]||n!==data.source.regions[i].faces))throw Error('Regional face counts differ from integrated evidence');
 return {positions,colors};
}
export function clearRegionalWall(){generation++;if(download)URL.revokeObjectURL(download);download=null;const e=document.getElementById('regional-wall-tools');if(e)e.hidden=true;const values=document.getElementById('regional-wall-values');if(values)values.hidden=true;}
export function mountRegionalWall(studies,load,draw,restore,available){
 clearRegionalWall();const token=generation,$=id=>document.getElementById(id),cache=new Map();let seq=0,current=null,visible=false;
 $('regional-wall-tools').hidden=false;$('regional-wall-values').hidden=false;$('regional-wall-case').replaceChildren();$('regional-wall-legend').replaceChildren();$('regional-wall-region').replaceChildren();$('regional-wall-loads').replaceChildren();$('regional-wall-note').textContent='Colors identify diagnostic neighborhoods, not stress. Uses the saved CFD wall mesh and native face-centre assignments.';$('regional-wall-download').hidden=true;
 for(const s of studies){const o=document.createElement('option');o.value=s.run_id;o.textContent=s.mesh_name+' / '+s.local_profile+' / '+s.domain_name;$('regional-wall-case').append(o);}
 for(const [i,label] of ['All neighborhoods',...['Base bore 1 neighborhood','Base bore 2 neighborhood','Upright bore 1 neighborhood','Upright bore 2 neighborhood','Root neighborhood','Base remainder','Upright remainder']].entries()){const o=document.createElement('option');o.value=i-1;o.textContent=label;$('regional-wall-region').append(o);}
 for(const [i,label] of ['Base bore 1','Base bore 2','Upright bore 1','Upright bore 2','Root','Base remainder','Upright remainder'].entries()){const span=document.createElement('span'),swatch=document.createElement('span');swatch.style.background=REGION_COLORS[i];swatch.className='region-swatch';span.append(swatch,document.createTextNode(label));$('regional-wall-legend').append(span);}
 $('regional-wall-show').disabled=!available;$('regional-wall-reset').disabled=true;
 const show=(fit=false)=>{
  if(!current||!visible)return;const selected=Number($('regional-wall-region').value),g=wallGeometry(current,selected);draw(g,fit);$('regional-wall-loads').replaceChildren();
  const rows=selected<0?current.source.regions:[current.source.regions[selected]],moment=$('regional-wall-quantity').value==='moment',suffix=moment?'_moment_N_m':'_force_N',unit=moment?'N·m':'N';
  for(const r of rows){const tr=document.createElement('tr');for(const text of [r.region,...['pressure','viscous','total'].map(k=>r.loads[k+suffix].map(v=>v.toExponential(3)).join(', ')+' '+unit)]){const td=document.createElement('td');td.textContent=text;tr.append(td);}$('regional-wall-loads').append(tr);}
  $('regional-wall-note').textContent=current.source.mesh+' · '+current.surface.wall_faces+' native wall faces · '+current.surface.triangles.length+' display triangles. '+(selected<0?'All neighborhoods shown.':current.regions[selected]+' highlighted; other faces dimmed.')+' Colors are region labels, not stress. Selected source '+current.source.run_id+'.';
 };
 const fetchCase=async()=>{
  const ticket=++seq,id=$('regional-wall-case').value;visible=true;current=null;$('regional-wall-note').textContent='Reproducing native source evidence and loading the wall mesh…';$('regional-wall-show').disabled=true;
  try{let d=cache.get(id);if(!d){d=await load(id);if(token!==generation||ticket!==seq)return;wallGeometry(d);cache.set(id,d);}if(token!==generation||ticket!==seq)return;
   if(d.source.run_id!==id||!Object.values(d.checks).every(v=>v===true))throw Error('Wall source identity or checks differ');current=d;visible=true;show(true);$('regional-wall-reset').disabled=false;
   if(download)URL.revokeObjectURL(download);download=URL.createObjectURL(new Blob([JSON.stringify(d)],{type:'application/json'}));$('regional-wall-download').href=download;$('regional-wall-download').hidden=false;
  }catch(e){if(token===generation&&ticket===seq)$('regional-wall-note').textContent=e.message;}finally{if(token===generation&&ticket===seq)$('regional-wall-show').disabled=!available;}
 };
 $('regional-wall-show').onclick=fetchCase;$('regional-wall-case').onchange=()=>{if(visible)fetchCase();};$('regional-wall-region').onchange=()=>show();$('regional-wall-quantity').onchange=()=>show();
 $('regional-wall-reset').onclick=()=>{seq++;visible=false;restore();$('regional-wall-show').disabled=!available;$('regional-wall-reset').disabled=true;$('regional-wall-loads').replaceChildren();$('regional-wall-note').textContent='Original PicoGK surface shown. Choose Show regions to inspect the saved CFD wall.';};
}
