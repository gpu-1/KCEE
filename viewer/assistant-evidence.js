import {textHash} from './search-export.js';
import {canonicalNoteJson} from './note-export.js';
export async function verifyAssistantEvidence(result){
 if(typeof result.evidence_canonical_json!=='string'||await textHash(result.evidence_canonical_json)!==result.evidence_sha256)throw new Error('AI canonical evidence hash mismatch');
 if(canonicalNoteJson(JSON.parse(result.evidence_canonical_json))!==canonicalNoteJson(result.evidence))throw new Error('AI displayed evidence differs from hashed evidence');
}
