import { fetchWithDeadline } from './requestTimeout';
import { isPackagedImage } from './mediaReferences';
import { validateAssetData } from './svgAssets';
import type { AssetKind } from './dashboardAssets';

/** User-requested portable export: conservative same-origin static files only. */
export async function readPackagedAsset(path: string, kind: AssetKind) {
  if (!isPackagedImage(path)) throw new Error('Only supported same-instance packaged media can be included.');
  return fetchWithDeadline(path,{credentials:'same-origin',redirect:'error'},20_000,async response=>{
    if (!response.ok || !response.body) throw new Error('A packaged asset is unavailable to your Splunk user.');
    const reader=response.body.getReader(), chunks:Uint8Array[]=[];let length=0;
    try {
      for(;;){const next=await reader.read();if(next.done)break;length+=next.value.length;if(length>4_000_000)throw new Error('A packaged asset exceeds 4 MB.');chunks.push(next.value);}
    } finally {await reader.cancel();}
    const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    const ext=path.split('.').at(-1)!.toLowerCase();
    // Splunk can negotiate WebP bytes at a PNG URL. Trust verified signatures,
    // while retaining exact response bytes and requiring passive SVG markup.
    const ascii=(a:number,b:number)=>String.fromCharCode(...bytes.slice(a,b));
    const mime=ext==='svg'?'svg+xml':bytes[0]===137&&ascii(1,4)==='PNG'?'png':bytes[0]===255&&bytes[1]===216?'jpeg':['GIF87a','GIF89a'].includes(ascii(0,6))?'gif':ascii(0,4)==='RIFF'&&ascii(8,12)==='WEBP'?'webp':'unknown';
    const dataURI=`data:image/${mime};base64,`+btoa(Array.from(bytes,byte=>String.fromCharCode(byte)).join(''));
    return {name:path.split('/').at(-1)!,dataURI:validateAssetData(dataURI,kind)};
  });
}
