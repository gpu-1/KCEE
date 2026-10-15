const key='kcee.saved-searches.v1';
export function validateSavedSearches(value){
 if(!Array.isArray(value)||value.length>50)throw new Error('Invalid saved search list');
 for(const r of value){if(!r||typeof r.id!=='string'||!r.id||r.id.length>100||typeof r.question!=='string'||!r.question.trim()||r.question.length>800||!Number.isFinite(Date.parse(r.saved_at))||!(r.document===null||(r.document&&/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(r.document.id)&&typeof r.document.name==='string'&&r.document.name.length<=255)))throw new Error('Invalid saved search');}
 if(new Set(value.map(r=>r.id)).size!==value.length)throw new Error('Duplicate saved search identity');return value;
}
export function loadSavedSearches(storage){const raw=storage.getItem(key);if(raw&&raw.length>100000)throw new Error('Saved search storage exceeds its limit');return validateSavedSearches(raw?JSON.parse(raw):[]);}
export function saveSearch(storage,question,document=null,now=new Date().toISOString()){
 question=question.trim();const rows=loadSavedSearches(storage),existing=rows.find(r=>r.question===question&&(r.document?.id||null)===(document?.id||null));
 if(!existing&&rows.length>=50)throw new Error('50 searches saved. Remove one before saving another.');
 const record={id:existing?.id||crypto.randomUUID(),question,document:document?{id:document.id,name:document.name}:null,saved_at:now};const next=[record,...rows.filter(r=>r.id!==record.id)];validateSavedSearches(next);storage.setItem(key,JSON.stringify(next));return next;
}
export function removeSavedSearch(storage,id){const next=loadSavedSearches(storage).filter(r=>r.id!==id);storage.setItem(key,JSON.stringify(next));return next;}

export function mergeSavedSearches(storage,incoming,apply=false){
 validateSavedSearches(incoming);const rows=loadSavedSearches(storage),next=structuredClone(rows);let skipped=0;
 for(const row of incoming){const question=row.question.trim(),document=row.document?{id:row.document.id.toLowerCase(),name:row.document.name}:null;
  if(next.some(r=>r.question.trim()===question&&(r.document?.id?.toLowerCase()||null)===(document?.id||null))){skipped++;continue;}
  next.push({id:crypto.randomUUID(),question,document,saved_at:row.saved_at});}
 if(next.length>50)throw new Error('Import would exceed 50 saved searches. No searches were changed.');validateSavedSearches(next);
 if(apply)storage.setItem(key,JSON.stringify(next));return {rows:next,added:next.length-rows.length,skipped};
}
