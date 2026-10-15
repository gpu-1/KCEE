import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyAssistantEvidence} from '../assistant-evidence.js';
import {textHash} from '../search-export.js';
test('exact hashed evidence survives browser number formatting and rejects changed evidence',async()=>{
 const raw='{"heat":1.0,"small":1e-07}',result={evidence_canonical_json:raw,evidence_sha256:await textHash(raw),evidence:JSON.parse(raw)};await verifyAssistantEvidence(result);result.evidence.heat=2;await assert.rejects(verifyAssistantEvidence(result),/differs/);result.evidence_canonical_json='{}';await assert.rejects(verifyAssistantEvidence(result),/hash/);
});
