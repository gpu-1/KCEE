export function filterDocuments(items,{name='',type='all',sort='newest'}={}){
 const query=name.trim().toLocaleLowerCase();
 const result=items.filter(item=>item.name.toLocaleLowerCase().includes(query)&&(type==='all'||item.name.toLowerCase().endsWith('.'+type)));
 const nameOrder=(a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'})||String(a.id).localeCompare(String(b.id));
 const date=item=>Date.parse(item.created_at)||0;
 const comparators={newest:(a,b)=>date(b)-date(a)||nameOrder(a,b),oldest:(a,b)=>date(a)-date(b)||nameOrder(a,b),name:nameOrder,size:(a,b)=>b.bytes-a.bytes||nameOrder(a,b)};
 return result.sort(comparators[sort]||comparators.newest);
}
