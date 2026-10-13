export class ApiError extends Error {
  constructor(status, detail) { super(typeof detail === 'string' ? detail : detail?.message || `Request failed (${status})`); this.status = status; this.detail = detail; }
}
export async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    let detail; try { detail = (await response.json()).detail; } catch { detail = 'Service unavailable. Check the local API.'; }
    throw new ApiError(response.status, detail);
  }
  return response.json();
}
export function artifactUrl(id, name) {
  if (!/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(id)) throw new Error('Invalid run identifier');
  if (!['bracket.stl','result.json','report.md','manifest.json','fea-artifacts.zip'].includes(name)) throw new Error('Unsupported artifact');
  return `/api/artifacts/${id}/${name}`;
}
export async function verifiedBytes(id, name, digest, signal) {
  if (!/^[a-f0-9]{64}$/.test(digest || '')) throw new Error('Missing artifact hash');
  const response = await fetch(artifactUrl(id, name), {signal});
  if (!response.ok) throw new ApiError(response.status, 'Unable to download '+name);
  const bytes = await response.arrayBuffer();
  const actual = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2,'0')).join('');
  if (actual !== digest) throw new Error('Artifact integrity check failed: '+name);
  return bytes;
}
export async function loadRun(id, signal) {
  const record = await request(`/runs/${id}`, {signal});
  if (record.id !== id || record.manifest?.run_id !== id) throw new Error('Run identity mismatch');
  const verification = await request(`/runs/${id}/verify`, {signal});
  if (verification.integrity !== 'verified' || verification.run_id !== id) throw new Error('Run integrity could not be verified');
  const [stl, raw] = await Promise.all([
    verifiedBytes(id,'bracket.stl',record.manifest.artifacts['bracket.stl'],signal),
    verifiedBytes(id,'result.json',record.manifest.artifacts['result.json'],signal),
  ]);
  const result = JSON.parse(new TextDecoder().decode(raw));
  if (result.validation_status !== record.validation_status) throw new Error('Result status differs from saved record');
  return {record,result,stl};
}

export function comparisonEvidence(reference,selected,measures,difference){
  const source=study=>{
    const record=study.record;
    if(record.id!==record.manifest?.run_id || study.result.kind!=='bracket_structural' || study.result.validation_status!==record.validation_status)throw new Error('Invalid comparison identity or status');
    const hashes=[record.manifest_sha256,record.manifest.artifacts['bracket.stl'],record.manifest.artifacts['fea-artifacts.zip']];
    if(!hashes.every(value=>/^[a-f0-9]{64}$/.test(value||'')))throw new Error('Missing comparison provenance');
    return {run_id:record.id,manifest_sha256:hashes[0],source_stl_sha256:hashes[1],solver_archive_sha256:hashes[2],validation_status:record.validation_status};
  };
  if(!Number.isFinite(difference))throw new Error('Invalid displacement comparison');
  return {schema_version:1,exported_at:new Date().toISOString(),reference:source(reference),selected:source(selected),measures,loaded_displacement_change_percent:difference,limitations:['Geometry, meshing and load-patch discretization may differ','Stress peaks remain unconverged','Artifact verification does not establish engineering acceptance']};
}

export function comparisonMarkdown(report){
  const cell=value=>String(value??'Not recorded').replace(/\|/g,'\\|').replace(/[\r\n]+/g,' ');
  return ['# KCEE saved bracket study comparison','',`Exported: ${report.exported_at}`,'','This is a derived comparison of verified saved runs. Engineering validation remains pending.','',`Reference run: ${report.reference.run_id}`,`Selected run: ${report.selected.run_id}`,'','| Measure | Reference | Selected |','|---|---|---|',...report.measures.map(row=>`| ${cell(row.measure)} | ${cell(row.reference)} | ${cell(row.selected)} |`),'',`Loaded displacement change: ${report.loaded_displacement_change_percent}%`,'','## Source provenance','',...['reference','selected'].flatMap(key=>{const source=report[key];return [`${key}: ${source.run_id}`,`Manifest SHA-256: ${source.manifest_sha256}`,`STL SHA-256: ${source.source_stl_sha256}`,`Solver archive SHA-256: ${source.solver_archive_sha256}`,`Recorded validation: ${source.validation_status}`,''];}),'## Interpretation limits','',...report.limitations.map(text=>'- '+cell(text)),''].join('\n');
}

export function studyMarkdown(study,diagnostic=null){
  const provenance=comparisonEvidence(study,study,[],0).selected,fea=study.result.fea;
  const line=value=>String(value??'Not recorded').replace(/[\r\n]+/g,' ').replace(/\|/g,'\\|');
  return ['# KCEE bracket structural study','',`Run: ${provenance.run_id}`,`Parent design: ${study.record.parent_id||'Not recorded'}`,`Recorded validation: ${provenance.validation_status}`,'','Engineering validation remains pending. This is a derived readable report; original saved artifacts are unchanged.','','## Assumptions','',`Support: ${line(fea.boundary)}`,`Load: ${line(fea.load)}`,`Material: E=${fea.material?.youngs_modulus_MPa??'Not recorded'} MPa; Poisson ratio=${fea.material?.poisson_ratio??'Not recorded'}`,`Geometry: ${line(study.result.geometry_backend)}`,`Surface classification: ${fea.surface_classification_angle_degrees??'Not recorded'} degrees`,'','## Mesh study','', '| Target (mm) | Elements | Loaded displacement (mm) | Peak stress (MPa, unconverged) |','|---|---|---|---|',...fea.mesh_study.map(m=>`| ${m.target_size_mm} | ${m.elements} | ${m.tip_deflection_mm} | ${m.maximum_von_mises_MPa} |`),'','## Recorded numerical checks','',...Object.entries(fea.checks).map(([name,pass])=>`- ${line(name)}: ${pass===true?'Pass':pass===false?'Needs attention':'Not recorded'}`),'','## Retrospective diagnostics','',diagnostic?`Source load-area agreement: ${diagnostic.source_load_patch_agreement?'Pass':'Needs attention'}; ${(diagnostic.relative_source_load_patch_area_error*100).toFixed(3)}% error`:'Retrospective diagnostics unavailable; do not infer acceptance.',...(diagnostic?.regional_refinement?.last_changes||[]).map(r=>`Regional stress change (centroids ≥${r.centroid_exclusion_distance_mm} mm from nominal clamp/load): ${r.relative_last_peak_change===null?'Not available':(100*r.relative_last_peak_change).toFixed(3)+'%'}; informational`),'','## Provenance','',`Manifest SHA-256: ${provenance.manifest_sha256}`,`STL SHA-256: ${provenance.source_stl_sha256}`,`Solver archive SHA-256: ${provenance.solver_archive_sha256}`,'','## Limits','',line(fea.stress_note),'Stable displacement does not establish stable stress. Numerical checks and artifact integrity do not establish engineering acceptance.',''].join('\n');
}

export function numericalCheckRows(fea){
  const rows=[['force_balance','Force balance',Math.max(...fea.mesh_study.map(m=>Math.abs(m.reaction_z_N-100)/100))],['displacement_refinement','Last displacement change',fea.last_mesh_displacement_change],['load_patch_refinement','Last load-patch area change',fea.last_load_patch_area_change],['source_volume_agreement','Source volume error',fea.relative_source_volume_error],['load_patch_source_agreement','Load-strip area vs original STL',fea.relative_source_load_patch_area_error]];
  return rows.map(([key,label,value])=>({key,label,value,verdict:fea.checks[key]===true?'Pass':fea.checks[key]===false?'Needs attention':'Not recorded'}));
}
