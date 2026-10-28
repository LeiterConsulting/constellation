import { describe, expect, it, vi } from 'vitest';
import { DashboardDefinition } from '@splunk/dashboard-definition';
import { getCompleteSearchQuery } from '@splunk/datasource-utils';
import { createBlank, previewDefinition } from './document';
import { hasSharedImages, placeDashboardImage, previewImage } from './dashboardAssets';

describe('native shared images and safe preview', () => {
  it('retains native and packaged image references while pausing external URLs/actions', () => {
    const doc=createBlank();doc.visualizations={image:{type:'splunk.image',options:{src:'splunk-enterprise-kvstore://fixture_image',href:'https://example.com',preserveAspectRatio:true}}, external:{type:'splunk.image',options:{src:'https://example.com/a.png'}}};
    const before=structuredClone(doc), preview=previewDefinition(doc);
    expect(preview.visualizations.image.options?.src).toBe(doc.visualizations.image.options?.src);
    expect(preview.visualizations.image.options?.href).toBeUndefined();expect(preview.visualizations.external.options?.src).toBeUndefined();expect(doc).toEqual(before);
    expect(previewImage('/static/app/constellation/appIcon.png')).toBe(true);
    for(const src of ['javascript:alert(1)','//example.com/a.png','splunk-enterprise-kvstore://../x','/static/app/x/../x.png','/static/app/x/%2e%2e/x.png'])expect(previewImage(src)).toBe(false);
  });
  it('replaces only a selected icon and preserves its metric bindings',()=>{
    const doc=createBlank();doc.dataSources={s:{type:'ds.search',options:{query:'| stats count'}}};doc.visualizations.icon={type:'splunk.singlevalueicon',options:{icon:'splunk-enterprise-kvstore://old',showValue:true},dataSources:{primary:'s'},future:{keep:true}};const before=structuredClone(doc), changed=placeDashboardImage(doc,{id:'new_icon',name:'New',kind:'icon'},'layout_main','icon');const expected=structuredClone(doc);expected.visualizations.icon.options!.icon='splunk-enterprise-kvstore://new_icon';expect(changed.definition).toEqual(expected);expect(doc).toEqual(before);
  });
  it('replaces only a selected choropleth asset without changing bindings or events',()=>{
    const doc=createBlank();doc.visualizations.map={type:'splunk.choropleth.svg',options:{svg:'splunk-enterprise-kvstore://old',areaIds:'> primary | seriesByName(\"area\")'},dataSources:{primary:'s'},future:{keep:true}};doc.dataSources={s:{type:'ds.search',options:{query:'| stats count by area'}}};const expected=structuredClone(doc);expected.visualizations.map.options!.svg='splunk-enterprise-kvstore://new_map';expect(placeDashboardImage(doc,{id:'new_map',name:'Map',kind:'image',usage:'map'},'layout_main','map').definition).toEqual(expected);
  });
  it('adds below existing work, replaces only the selected image reference and rejects a grid page', () => {
    const nativeCrypto=globalThis.crypto;vi.stubGlobal('crypto',{getRandomValues:nativeCrypto.getRandomValues.bind(nativeCrypto)});
    const doc=createBlank();doc.visualizations.keep={type:'splunk.table',future:{retain:true}};
    const layouts=doc.layout.layoutDefinitions as Record<string,{structure:unknown[];type:string}>;layouts.layout_main.structure=[{item:'keep',type:'block',position:{x:20,y:700,w:100,h:200}}];
    const before=structuredClone(doc),placed=placeDashboardImage(doc,{id:'fixture_image',name:'Fixture'},'layout_main');
    expect(doc).toEqual(before);expect(placed.definition.visualizations.keep).toEqual(doc.visualizations.keep);expect(hasSharedImages(placed.definition)).toBe(true);
    const changed=placeDashboardImage(placed.definition,{id:'other_image',name:'Other'},'layout_main',placed.id);
    const expected=structuredClone(placed.definition);expected.visualizations[placed.id].options!.src='splunk-enterprise-kvstore://other_image';expect(changed.definition).toEqual(expected);
    layouts.layout_main.type='grid';expect(()=>placeDashboardImage(doc,{id:'fixture_image',name:'Fixture'})).toThrow('absolute');vi.stubGlobal('crypto',nativeCrypto);
  });
});

describe('native cascading snapshots',()=>{
  it('preserves query and chain dependency metadata in inert snapshot sources',()=>{
    const doc=createBlank();doc.dataSources={base:{type:'ds.search',options:{query:'search index="fixture" parent=$parent|s$'}},child:{type:'ds.chain',options:{extend:'base',query:'| stats count by child'}}};
    doc.inputs={child:{type:'input.dropdown',options:{token:'child',isCascadingInput:true,defaultValue:'*'},dataSources:{primary:'child'}}};
    const before=structuredClone(doc),preview=previewDefinition(doc,{}, {default:{parent:'A',child:'B'}});
    expect(Object.values(preview.dataSources!).every(ds=>ds.type==='ds.test' && !ds.options?.extend)).toBe(true);
    const query=getCompleteSearchQuery({definition:DashboardDefinition.fromJSON(preview as never),dataSourceId:'child'});
    expect(query).toContain('$parent|s$');expect(query).toContain('stats count by child');expect(doc).toEqual(before);
  });
});
