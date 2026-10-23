import { validateDefinition, type JsonObject, type StudioDefinition } from './document';

export type PagePurpose = Record<string,string>;
export interface PageInfo { id: string; name: string; purpose: string; items: string[]; }
export function pagesOf(definition: StudioDefinition, purposes: PagePurpose = {}): PageInfo[] {
  const layouts = definition.layout.layoutDefinitions as Record<string,{structure?: Array<{item:string}>}> | undefined;
  const tabs = definition.layout.tabs as {items?:Array<{layoutId:string;label?:string}>} | undefined;
  return (tabs?.items || []).map(tab => ({id:tab.layoutId,name:tab.label || tab.layoutId,purpose:purposes[tab.layoutId] || '',
    items:layouts?.[tab.layoutId]?.structure?.map(item=>item.item) || []}));
}
export function elementsOf(definition: StudioDefinition) {
  return [...Object.entries(definition.visualizations).map(([id,item])=>({id,label:item.title || id,kind:'visualization' as const})),
    ...Object.entries((definition.inputs || {}) as Record<string,{title?:string;options?:{label?:string}}>).map(([id,item])=>({id,label:item.title || item.options?.label || id,kind:'input' as const}))];
}
export const validFocus = (definition:StudioDefinition, id:string) => !id || (id.startsWith('page:') ? pagesOf(definition).some(page=>page.id===id.slice(5)) : elementsOf(definition).some(item=>item.id===id));
export function navigationTarget(definition:StudioDefinition, id:string, field?:unknown):string | undefined {
  const source=definition.visualizations[id] || (definition.inputs as Record<string,JsonObject> | undefined)?.[id];
  const handlers=source?.eventHandlers as Array<{type:string;options?:{fields?:string[];tokens?:Array<{token:string;value?:unknown}>}}> | undefined;
  const token=handlers?.filter(handler=>handler.type==='drilldown.setToken'&&(!handler.options?.fields?.length||handler.options.fields.includes(String(field))))
    .flatMap(handler=>handler.options?.tokens||[]).find(token=>token.token==='constellation_focus');
  return typeof token?.value==='string'&&token.value&&validFocus(definition,token.value)?token.value:undefined;
}
export function changePage(definition:StudioDefinition, id:string, name:string): StudioDefinition {
  if (!name.trim() || name.length>200) throw new Error('Give the page a name under 200 characters.');
  const result=structuredClone(definition);
  if (!result.layout.layoutDefinitions && (result.layout.structure as unknown[] | undefined)?.length) throw new Error('Convert this legacy layout to native Studio pages before adding a page. Its existing elements are preserved.');
  const layouts=(result.layout.layoutDefinitions ||= {}) as Record<string,JsonObject>;
  const tabs=(result.layout.tabs ||= {items:[]}) as {items:Array<{layoutId:string;label:string}>};
  if (!Object.hasOwn(layouts,id)) {
    if (Object.keys(layouts).length>=30) throw new Error('This draft supports up to 30 pages.');
    layouts[id]={type:'absolute',options:{width:1200,height:800,display:'auto-scale'},structure:[]};
    tabs.items.push({layoutId:id,label:name.trim()});
  } else {const tab=tabs.items.find(tab=>tab.layoutId===id);if(tab)tab.label=name.trim();}
  return validateDefinition(result);
}
export interface WorkspaceRoute { draft?:string; page?:string; focus?:string; }
export function readWorkspaceRoute(value:string):WorkspaceRoute {
  const url=new URL(value),draft=url.searchParams.get('draft') || '';
  return {draft:/^[a-f0-9]{32}$/.test(draft)?draft:undefined,page:url.searchParams.get('tab') || undefined,focus:url.searchParams.get('focus') || undefined};
}
export function workspaceLink(base:string,draft:string,page?:string,focus?:string) {
  if(!/^[a-f0-9]{32}$/.test(draft))throw new Error('Save this draft before copying a link.');
  const url=new URL(base);url.hash='';
  for(const key of [...url.searchParams.keys()])if(key==='draft'||key==='tab'||key==='focus'||key.startsWith('form.'))url.searchParams.delete(key);
  url.searchParams.set('draft',draft);if(page)url.searchParams.set('tab',page);if(focus)url.searchParams.set('focus',focus);
  return url.href;
}
