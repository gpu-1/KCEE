export function libraryQuery({includeArchived=false,page=1,pageSize=25,name='',type='all',sort='newest'}={}){
 return '/knowledge/library?'+new URLSearchParams({include_archived:String(includeArchived),page:String(page),page_size:String(pageSize),name,file_type:type,sort});
}
export function libraryPageLabel(data){
 if(!data.total)return 'No documents match these filters.';
 const first=(data.page-1)*data.page_size+1,last=first+data.items.length-1;
 return first+'–'+last+' of '+data.total+' matching documents · Page '+data.page+' of '+data.pages;
}
