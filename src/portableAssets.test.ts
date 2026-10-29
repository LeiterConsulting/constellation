import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { DOMParser as XmlParser } from '@xmldom/xmldom';
import { createBlank } from './document';
import { svgDataUri, validateSvg, validateAssetData } from './svgAssets';
import { assetReferences, exportPortable, importPortable, readPortable } from './portableAssets';
import { prepareDependencies, checkDependencies, importDependencies } from './dashboardDependencies';
import { readPackagedAsset } from './packagedAssets';
import { readAssetData, uploadAssetData } from './dashboardAssets';
vi.mock('./dashboardDependencies',()=>({prepareDependencies:vi.fn(async definition=>({definition:structuredClone(definition),dependencies:[],notes:[],blocked:false})),checkDependencies:vi.fn(async definition=>({definition,dependencies:[],notes:[],blocked:false})),importDependencies:vi.fn(async definition=>({definition:structuredClone(definition),dependencies:[],notes:[],blocked:false}))}));
vi.mock('./packagedAssets',()=>({readPackagedAsset:vi.fn()}));
vi.mock('./dashboardAssets',()=>({readAssetData:vi.fn(),uploadAssetData:vi.fn()}));
const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path id="area" fill="currentColor" d="M2 2h20v20H2z"/></svg>';
beforeAll(()=>{ vi.stubGlobal('DOMParser',class {parseFromString(text: string) {return new XmlParser({errorHandler:{warning:()=>{throw Error('XML');},error:()=>{throw Error('XML');},fatalError:()=>{throw Error('XML');}}}).parseFromString(text,'image/svg+xml');}}); });
beforeEach(()=>vi.clearAllMocks());
function board() { const d=createBlank();d.visualizations={a:{type:'splunk.singlevalueicon',options:{icon:'splunk-enterprise-kvstore://same',showValue:false},future:{keep:true}},b:{type:'splunk.singlevalueicon',options:{icon:'splunk-enterprise-kvstore://same'}}};return d; }
describe('passive SVG boundary',()=>{
 it('preserves exact Unicode text, shapes and local gradient references',()=>{
  expect(validateSvg(svg)).toBe(svg);expect(validateAssetData(svgDataUri(svg),'icon')).toBe(svgDataUri(svg));
  expect(validateSvg(svg.replace('<path','<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs><path').replace('currentColor','url(#g)'))).toContain('url(#g)');
 });
 it('rejects active markup, foreign namespaces, resource requests, CSS, entities and oversized input',()=>{
  for(const content of ['<script>alert(1)</script>','<foreignObject/>','<image href="https://example.com/a.png"/>','<path onload="x"/>','<path style="fill:red"/>','<path fill="url(https://example.com)"/>','<use href="data:image/svg+xml;base64,abc"/>','<path xmlns="https://example.com"/>']) expect(()=>validateSvg(svg.replace('<path id="area" fill="currentColor" d="M2 2h20v20H2z"/>',content))).toThrow();
  expect(()=>validateSvg('<!DOCTYPE svg [<!ENTITY x "x">]>'+svg)).toThrow();expect(()=>validateSvg(svg+' '.repeat(500_000))).toThrow();
 });
 it('validates media bytes and canonical base64 rather than trusting a declared MIME',()=>{
  expect(()=>validateAssetData('data:image/png;base64,'+btoa('wrong'),'image')).toThrow();expect(validateAssetData(svgDataUri(svg),'image')).toBe(svgDataUri(svg));
 });
});
describe('portable native assets',()=>{
 it('deduplicates per collection, verifies checksums and remaps only exact slots',async()=>{
  const d=board(),before=structuredClone(d);vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});vi.mocked(uploadAssetData).mockResolvedValue({id:'destination',name:'Fixture.svg',kind:'icon'});
  const file=await exportPortable(d,()=>{});expect(file.assets).toHaveLength(1);expect(readAssetData).toHaveBeenCalledTimes(1);expect(await readPortable(file)).toEqual(file);
  const moved=await importPortable(file,()=>{});expect(uploadAssetData).toHaveBeenCalledTimes(1);expect(moved.visualizations.a.options?.icon).toBe('splunk-enterprise-kvstore://destination');expect(moved.visualizations.a.future).toEqual({keep:true});expect(d).toEqual(before);
 });
 it('rejects tampered, unrelated, duplicate, missing and unsafe assets before any upload',async()=>{
  vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(board(),()=>{});
  const bad=structuredClone(file);bad.assets[0].dataURI=svgDataUri(svg.replace('M2','M3'));await expect(importPortable(bad,()=>{})).rejects.toThrow('checksum');
  await expect(importPortable({...file,assets:[]},()=>{})).rejects.toThrow('missing');await expect(importPortable({...file,assets:[...file.assets,...file.assets]},()=>{})).rejects.toThrow('duplicate');expect(uploadAssetData).not.toHaveBeenCalled();
 });
 it('keeps equal image/icon IDs separate and refuses dynamic or unclassified references',()=>{
  const d=board();d.visualizations.image={type:'splunk.image',options:{src:'splunk-enterprise-kvstore://same'}};expect(assetReferences(d).map(x=>x.kind)).toEqual(['icon','icon','image']);
  d.description='splunk-enterprise-kvstore://same';expect(()=>assetReferences(d)).toThrow('unsupported');
 });
 it('does not replay uncertain uploads or return a partially changed dashboard',async()=>{
  const d=board();vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(d,()=>{});vi.mocked(uploadAssetData).mockRejectedValue(Error('interrupted'));
  await expect(importPortable(file,()=>{})).rejects.toThrow('Your draft is unchanged');expect(uploadAssetData).toHaveBeenCalledTimes(1);expect(d).toEqual(board());
 });
 it('reports verified partial uploads without replay or partial document acceptance',async()=>{
  const d=board();d.visualizations.b.options!.icon='splunk-enterprise-kvstore://second';vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(d,()=>{});
  vi.mocked(uploadAssetData).mockResolvedValueOnce({id:'new_first',name:'Fixture.svg',kind:'icon'}).mockRejectedValueOnce(Error('connection interrupted'));
  await expect(importPortable(file,()=>{})).rejects.toThrow('1 shared assets verified');expect(uploadAssetData).toHaveBeenCalledTimes(2);expect(d.visualizations.a.options!.icon).toBe('splunk-enterprise-kvstore://same');
 });
 it('bundles packaged choropleth SVGs and preserves version-1 files',async()=>{
  const d=board();d.visualizations.map={type:'splunk.choropleth.svg',options:{svg:'/static/app/fixture/floor.svg'}};vi.mocked(readAssetData).mockResolvedValue({name:'icon.svg',dataURI:svgDataUri(svg)});vi.mocked(readPackagedAsset).mockResolvedValue({name:'floor.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(d,()=>{});expect(file.version).toBe(3);expect(file.assets).toHaveLength(2);expect(file.definition.visualizations.map.options!.svg).toMatch(/^splunk-enterprise-kvstore:\/\/packaged_/);expect(await readPortable(file)).toEqual(file);const old=await exportPortable(board(),()=>{});old.version=1;delete old.lookups;expect((await readPortable(old)).version).toBe(1);
 });
 it('imports validated lookup copies before media and preserves the returned query remapping',async()=>{
  const definition=board();definition.dataSources={s:{type:'ds.search',options:{query:'| inputlookup fixture.csv'}}};
  const lookups=[{kind:'lookup' as const,name:'fixture.csv',app:'constellation' as const,fields:['name'],rows:[['Fixture']],fingerprint:'a'.repeat(64)}];
  const remapped=structuredClone(definition);remapped.dataSources!.s.options!.query='| inputlookup fresh.csv';
  vi.mocked(prepareDependencies).mockResolvedValueOnce({definition,dependencies:[],notes:[],blocked:false,lookups});vi.mocked(readAssetData).mockResolvedValue({name:'icon.svg',dataURI:svgDataUri(svg)});vi.mocked(uploadAssetData).mockResolvedValue({id:'destination',name:'icon.svg',kind:'icon'});
  const file=await exportPortable(definition,()=>{},()=>false,false,true);expect(prepareDependencies).toHaveBeenLastCalledWith(definition,false,true);
  vi.mocked(importDependencies).mockResolvedValueOnce({definition:remapped,dependencies:[],notes:[],blocked:false});
  const result=await importPortable(file,()=>{});expect(importDependencies).toHaveBeenCalledWith(definition,[],lookups);expect(importDependencies).toHaveBeenCalledTimes(1);expect(result.dataSources!.s.options!.query).toContain('fresh.csv');
  expect(vi.mocked(importDependencies).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(uploadAssetData).mock.invocationCallOrder[0]);expect(file.definition.dataSources!.s.options!.query).toContain('fixture.csv');
 });
 it('stops before media after uncertain lookup creation and refuses lookups in old file versions',async()=>{
  vi.mocked(readAssetData).mockResolvedValue({name:'icon.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(board(),()=>{});file.lookups=[{kind:'lookup',name:'fixture.csv',app:'constellation',fields:['name'],rows:[],fingerprint:'b'.repeat(64)}];
  vi.mocked(importDependencies).mockRejectedValueOnce(Error('unverified lookup'));
  await expect(importPortable(file,()=>{})).rejects.toThrow('private lookup copies may have completed');expect(importDependencies).toHaveBeenCalledTimes(1);expect(uploadAssetData).not.toHaveBeenCalled();
  await expect(readPortable({...file,version:2})).rejects.toThrow('portable lookups');
 });
 it('checks missing destination dependencies before any upload',async()=>{
  vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(board(),()=>{});vi.mocked(checkDependencies).mockResolvedValueOnce({definition:file.definition,dependencies:[{kind:'index',name:'missing_fixture',app:'',status:'missing',detail:'Not listed'}],notes:[],blocked:true});await expect(importPortable(file,()=>{})).rejects.toThrow('before uploading');expect(uploadAssetData).not.toHaveBeenCalled();
 });
 it('supports a plain HTTP host without WebCrypto and uses standard SHA-256',async()=>{
  const nativeCrypto=globalThis.crypto;vi.stubGlobal('crypto',{getRandomValues:nativeCrypto.getRandomValues.bind(nativeCrypto)});
  try {vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(board(),()=>{});const bytes=await nativeCrypto.subtle.digest('SHA-256',new TextEncoder().encode(file.assets[0].dataURI));expect(file.assets[0].sha256).toBe(Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join(''));expect(await readPortable(file)).toEqual(file);} finally {vi.stubGlobal('crypto',nativeCrypto);}
 });
 it('cancels an export before reading assets',async()=>{await expect(exportPortable(board(),()=>{},()=>true)).rejects.toThrow('cancelled');expect(readAssetData).not.toHaveBeenCalled();});
});
