const panels=['library','search','compare','verify','review','backup'];let previousRoute=null;
export function workspaceRoute(hash){if(hash==='#documents')return 'library';if(!hash.startsWith('#documents/'))return null;const key=hash.slice(11);return panels.includes(key)?key:'library';}
function applyRoute(){
 const route=workspaceRoute(location.hash),changed=route!==previousRoute,wasOpen=previousRoute!==null;previousRoute=route;
 document.getElementById('design-workspace').hidden=route!==null;document.getElementById('knowledge-dialog').hidden=route===null;
 document.getElementById('workspace-title').textContent=route?'Document workspace':'Design workspace';document.title='KCEE · '+(route?'Document workspace':'Design workspace');
 for(const panel of document.querySelectorAll('[data-document-panel]'))panel.hidden=panel.dataset.documentPanel!==route;
 for(const link of document.querySelectorAll('[data-document-tab]')){if(link.dataset.documentTab===route)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 if(route&&changed){window.scrollTo(0,0);const heading=document.getElementById('documents-'+route).querySelector('h3');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}
 if(route&&!wasOpen)document.dispatchEvent(new CustomEvent('kcee-documents-open'));
}
export function showDocumentPanel(panel='library'){location.hash='documents/'+(panels.includes(panel)?panel:'library');applyRoute();}
export function closeDocumentWorkspace(){location.hash='';applyRoute();document.getElementById('open-knowledge').focus({preventScroll:true});}
if(typeof window!=='undefined'&&typeof document!=='undefined'){
 window.addEventListener('hashchange',applyRoute);document.getElementById('close-documents').onclick=closeDocumentWorkspace;
 const search=document.getElementById('knowledge-search-question'),compare=document.getElementById('comparison-question');
 search.addEventListener('input',()=>{compare.value=search.value;});compare.addEventListener('input',()=>{search.value=compare.value;search.dispatchEvent(new Event('input',{bubbles:true}));});
 queueMicrotask(applyRoute);
}
