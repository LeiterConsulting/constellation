import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { DOMParser as XmlParser } from '@xmldom/xmldom';
import { createBlank } from './document';
import { svgDataUri, validateSvg, validateAssetData } from './svgAssets';
import { assetReferences, exportPortable, importPortable, readPortable } from './portableAssets';
import { readAssetData, uploadAssetData } from './dashboardAssets';
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
  expect(()=>validateAssetData('data:image/png;base64,'+btoa('wrong'),'image')).toThrow();expect(()=>validateAssetData(svgDataUri(svg),'image')).toThrow();
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
  await expect(importPortable(file,()=>{})).rejects.toThrow('1 assets verified');expect(uploadAssetData).toHaveBeenCalledTimes(2);expect(d.visualizations.a.options!.icon).toBe('splunk-enterprise-kvstore://same');
 });
 it('supports a plain HTTP host without WebCrypto and uses standard SHA-256',async()=>{
  const nativeCrypto=globalThis.crypto;vi.stubGlobal('crypto',{getRandomValues:nativeCrypto.getRandomValues.bind(nativeCrypto)});
  try {vi.mocked(readAssetData).mockResolvedValue({name:'Fixture.svg',dataURI:svgDataUri(svg)});const file=await exportPortable(board(),()=>{});const bytes=await nativeCrypto.subtle.digest('SHA-256',new TextEncoder().encode(file.assets[0].dataURI));expect(file.assets[0].sha256).toBe(Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join(''));expect(await readPortable(file)).toEqual(file);} finally {vi.stubGlobal('crypto',nativeCrypto);}
 });
 it('cancels an export before reading assets',async()=>{await expect(exportPortable(board(),()=>{},()=>true)).rejects.toThrow('cancelled');expect(readAssetData).not.toHaveBeenCalled();});
});
