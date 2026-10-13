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
