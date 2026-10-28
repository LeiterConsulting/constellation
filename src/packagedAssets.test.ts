import { afterEach, describe, expect, it, vi } from 'vitest';
import { readPackagedAsset } from './packagedAssets';
afterEach(()=>vi.unstubAllGlobals());
describe('bounded same-origin packaged media',()=>{
 it('recognizes negotiated WebP bytes at a PNG URL without changing the bytes',async()=>{
  const raw=new TextEncoder().encode('RIFF0000WEBPfixture');const fetch=vi.fn<typeof globalThis.fetch>(async()=>new Response(raw,{headers:{'Content-Type':'image/png'}}));vi.stubGlobal('fetch',fetch);
  const asset=await readPackagedAsset('/en-US/static/app/fixture/mark.png','image');expect(asset.dataURI).toBe('data:image/webp;base64,'+btoa('RIFF0000WEBPfixture'));expect(fetch.mock.calls[0][1]).toMatchObject({credentials:'same-origin',redirect:'error'});
 });
 it('rejects external/traversal paths before fetching and oversized/mismatched content',async()=>{
  const fetch=vi.fn<typeof globalThis.fetch>(async()=>new Response('not an image'));vi.stubGlobal('fetch',fetch);
  for(const path of ['https://example.com/a.png','//example.com/a.png','/static/app/x/../a.png','/static/app/x/a.png?next=elsewhere'])await expect(readPackagedAsset(path,'image')).rejects.toThrow('same-instance');expect(fetch).not.toHaveBeenCalled();
  await expect(readPackagedAsset('/static/app/fixture/a.png','image')).rejects.toThrow('Unsupported');
  fetch.mockImplementation(async()=>new Response(new Uint8Array(4_000_001)));await expect(readPackagedAsset('/static/app/fixture/a.png','image')).rejects.toThrow('exceeds');
 });
});
