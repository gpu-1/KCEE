// Highlight only whole literal query tokens; semantic relevance is a separate concern.
const words=/[\p{L}\p{N}]+(?:[.,][\p{N}]+)*/gu;
const ignored=new Set('a an and are as at be by for from how i in is it of on or that the this to was what when where which with does do de del el en es la las los o para por que qué un una y'.split(' '));
export function highlightSegments(content,question){
 const terms=new Set(Array.from(question.slice(0,800).matchAll(words),m=>m[0].toLowerCase()).filter(t=>!ignored.has(t)).slice(0,80));
 const segments=[];let end=0;
 for(const match of content.matchAll(words)){if(!terms.has(match[0].toLowerCase()))continue;if(match.index>end)segments.push({text:content.slice(end,match.index),match:false});segments.push({text:match[0],match:true});end=match.index+match[0].length;}
 if(end<content.length)segments.push({text:content.slice(end),match:false});return segments;
}
export function renderHighlightedPassage(element,content,question,enabled=true){
 element.replaceChildren();if(!enabled){element.textContent=content;return;}
 for(const part of highlightSegments(content,question)){const node=element.ownerDocument.createElement(part.match?'mark':'span');node.textContent=part.text;element.appendChild(node);}
}
