import { createFetchInit } from '@splunk/splunk-utils/fetch';
import { createRESTURL } from '@splunk/splunk-utils/url';
import ImageRegistry from '@splunk/visualization-context/ImageRegistry';
import IconRegistry from '@splunk/visualization-context/IconRegistry';
import Provider from '@splunk/visualization-context/Provider';
import { fetchWithDeadline } from './requestTimeout';
import { recoverRead } from './restDelivery';
import { isSplunk } from './api';
import { validateDefinition, type StudioDefinition } from './document';

import { assetType } from './mediaReferences';
import { svgDataUri, validateAssetData } from './svgAssets';
export { hasSharedImages, previewImage } from './mediaReferences';
export type AssetKind = 'image' | 'icon';
const collection = (kind: AssetKind) => kind === 'icon' ? 'splunk-dashboard-icons' : 'splunk-dashboard-images';
const validId = (id: unknown): id is string => typeof id === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(id);
export interface DashboardAsset { id: string; name: string; kind?: AssetKind; }

async function nativeAsset<T>(path: string, data?: Record<string, unknown>): Promise<T> {
  if (!isSplunk()) throw new Error('Open the installed Splunk app to use shared images.');
  const url = createRESTURL(path, { app: 'splunk-dashboard-studio', sharing: 'app' });
  return recoverRead(!data, 20_000, undefined, remaining => fetchWithDeadline(url, createFetchInit({
    method: data ? 'POST' : 'GET', body: data ? JSON.stringify(data) : undefined,
    headers: data ? { 'Content-Type': 'application/json' } : {},
  }), remaining, async response => {
    if (!response.ok) throw new Error(response.status === 403
      ? 'Your Splunk role cannot complete this shared asset request. Reuse an accessible asset or ask an administrator to review native Studio permissions.'
      : 'Splunk could not complete the image request. Check the shared image library before retrying an upload.');
    return response.json();
  }));
}

export async function listDashboardAssets(kind: AssetKind = 'image'): Promise<DashboardAsset[]> {
  const items = await nativeAsset<Array<{ _key: string; metaData?: { name?: string } }>>(`storage/collections/data/${collection(kind)}?limit=100&fields=_key,metaData.name`);
  if (!Array.isArray(items)) throw new Error('The Studio image library is unavailable.');
  return items.filter(item => validId(item._key)).map(item => ({ id: item._key, kind, name: typeof item.metaData?.name === 'string' ? item.metaData.name.slice(0, 200) : item._key }));
}
export async function readDashboardImage(file: File): Promise<string> {
  if (file.size > 4_000_000 || !file.size) throw new Error('Choose a file under 4 MB.');
  if (file.type === 'image/svg+xml' || /\.svg$/i.test(file.name)) return svgDataUri(await file.text());
  if (!['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type) || !file.size || file.size > 4_000_000) throw new Error('Choose a PNG, JPEG, GIF or WebP image under 4 MB.');
  const bytes = new Uint8Array(await file.slice(0, 16).arrayBuffer());
  const ascii = (start: number, end: number) => String.fromCharCode(...bytes.slice(start, end));
  const valid = file.type === 'image/png' ? [137,80,78,71,13,10,26,10].every((n,i) => bytes[i] === n)
    : file.type === 'image/jpeg' ? bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255
    : file.type === 'image/gif' ? ['GIF87a','GIF89a'].includes(ascii(0,6)) : ascii(0,4) === 'RIFF' && ascii(8,12) === 'WEBP';
  if (!valid) throw new Error('The file contents do not match its image type.');
  return new Promise((resolve,reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error('The image could not be read.')); reader.readAsDataURL(file); });
}
export async function uploadDashboardAsset(file: File): Promise<DashboardAsset> {
  const dataURI = await readDashboardImage(file);
  const kind: AssetKind = dataURI.startsWith('data:image/svg+xml;') ? 'icon' : 'image';
  const name = file.name.slice(0,200);
  return uploadAssetData({ name, kind, dataURI });
}
export async function uploadAssetData({ name, kind, dataURI }: { name: string; kind: AssetKind; dataURI: string }): Promise<DashboardAsset> {
  validateAssetData(dataURI, kind);
  const result = await nativeAsset<{ _key: string }>(`storage/collections/data/${collection(kind)}`, { dataURI, metaData: { name: name.slice(0,200) } });
  if (!validId(result._key)) throw new Error('The image may have uploaded, but its reference could not be verified. Check Studio before retrying.');
  const stored = await readAssetData(result._key, kind);
  if (stored.dataURI !== dataURI) throw new Error('The upload returned a reference, but its contents could not be verified. Check Studio before retrying.');
  return { id: result._key, name, kind };
}
export async function readAssetData(id: string, kind: AssetKind) {
  if (!validId(id)) throw new Error('Invalid Studio asset reference.');
  const result = await nativeAsset<{ dataURI?: string; metaData?: {name?: string} }>(`storage/collections/data/${collection(kind)}/${id}`);
  if (typeof result.dataURI !== 'string') throw new Error('This Studio asset is unavailable.');
  return { dataURI: validateAssetData(result.dataURI,kind), name: typeof result.metaData?.name === 'string' ? result.metaData.name.slice(0,200) : id };
}

class StudioImageProvider extends Provider {
  constructor(private kind: AssetKind = 'image') { super(); }
  getType() { return assetType; }
  async getById(id: string) {
    if (!validId(id)) throw new Error('Invalid Studio image reference.');
    const result = await readAssetData(id,this.kind);
    return { id, dataURI: result.dataURI };
  }
  async listIds() { return listDashboardAssets(this.kind); }
  async upload() { throw new Error('Use Dashboard images to upload.'); }
  async deleteById() { throw new Error('Manage shared images in native Studio.'); }
}
export function dashboardImageRegistry() { const registry = ImageRegistry.create(); registry.addDefaultProvider(new StudioImageProvider()); return registry; }
export function dashboardIconRegistry() { const registry = IconRegistry.create(); registry.addDefaultProvider(new StudioImageProvider('icon')); return registry; }

/** Explicit user selection; preserve the entire document and existing image geometry. */
export function placeDashboardImage(document: StudioDefinition, asset: DashboardAsset, activeTab?: string, selected?: string): { definition: StudioDefinition; id: string } {
  if (!validId(asset.id)) throw new Error('Choose an existing Studio image.');
  const definition = structuredClone(document);
  const src = `${assetType}://${asset.id}`;
  const image = selected && definition.visualizations[selected];
  const icon = asset.kind === 'icon';
  if (image && image.type === (icon ? 'splunk.singlevalueicon' : 'splunk.image')) { image.options = { ...image.options, [icon ? 'icon' : 'src']: src }; return { definition: validateDefinition(definition), id: selected }; }
  type Layout = { type?: string; options?: Record<string, unknown>; structure?: Array<{ position?: {x?: number; y?: number; w?: number; h?: number} } & Record<string, unknown>> };
  const layouts = definition.layout.layoutDefinitions as Record<string, Layout> | undefined;
  const target = layouts ? layouts[activeTab || Object.keys(layouts)[0]] : definition.layout as Layout;
  if (!target || target.type !== 'absolute') throw new Error('Choose an absolute-layout page to add an image.');
  const id = 'image_' + Array.from(crypto.getRandomValues(new Uint8Array(16)), byte=>byte.toString(16).padStart(2,'0')).join('');
  const y = Math.max(0,...(target.structure || []).map(item => Number(item.position?.y || 0) + Number(item.position?.h || 0))) + 20;
  const width = Number(target.options?.width || 1200);
  if (width < 100 || !Number.isFinite(y) || y > 100_000) throw new Error('This page has no supported space for a new image.');
  definition.visualizations[id] = icon ? { type: 'splunk.singlevalueicon', title: 'Icon', options: { icon: src, showValue: false, iconColor: '> themes.defaultFontColor' } } : { type: 'splunk.image', title: 'Image', options: { src, preserveAspectRatio: true } };
  target.structure = [...(target.structure || []), { type: 'block', item: id, position: { x: 20, y, w: Math.min(320,width-40), h: 160 } }];
  target.options = { ...target.options, height: Math.max(Number(target.options?.height || 800),y+200) };
  return { definition: validateDefinition(definition), id };
}
