import { describe, expect, it } from 'vitest';
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
  it('adds below existing work, replaces only the selected image reference and rejects a grid page', () => {
    const doc=createBlank();doc.visualizations.keep={type:'splunk.table',future:{retain:true}};
    const layouts=doc.layout.layoutDefinitions as Record<string,{structure:unknown[];type:string}>;layouts.layout_main.structure=[{item:'keep',type:'block',position:{x:20,y:700,w:100,h:200}}];
    const before=structuredClone(doc),placed=placeDashboardImage(doc,{id:'fixture_image',name:'Fixture'},'layout_main');
    expect(doc).toEqual(before);expect(placed.definition.visualizations.keep).toEqual(doc.visualizations.keep);expect(hasSharedImages(placed.definition)).toBe(true);
    const changed=placeDashboardImage(placed.definition,{id:'other_image',name:'Other'},'layout_main',placed.id);
    const expected=structuredClone(placed.definition);expected.visualizations[placed.id].options!.src='splunk-enterprise-kvstore://other_image';expect(changed.definition).toEqual(expected);
    layouts.layout_main.type='grid';expect(()=>placeDashboardImage(doc,{id:'fixture_image',name:'Fixture'})).toThrow('absolute');
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
