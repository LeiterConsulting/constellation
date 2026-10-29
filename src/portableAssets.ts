import sha256 from 'crypto-js/sha256';
import { validateDefinition, type StudioDefinition } from './document';
import { assetType, isNativeImage, isPackagedImage } from './mediaReferences';
import { readAssetData, uploadAssetData, type AssetKind } from './dashboardAssets';
import { prepareDependencies, checkDependencies, importDependencies, type DashboardDependency, type PortableLookup } from './dashboardDependencies';
import { readPackagedAsset } from './packagedAssets';
import { svgAreaIds, validateAssetData } from './svgAssets';

export interface PortableAsset { id: string; kind: AssetKind; name: string; dataURI: string; sha256: string; }
export interface PortableDashboard { format: 'constellation-dashboard'; version: 1|2|3; definition: StudioDefinition; assets: PortableAsset[]; dependencies?: DashboardDependency[]; notes?: string[]; lookups?: PortableLookup[]; }
type Reference = { path: string[]; id: string; kind: AssetKind; packaged?: string };
const key = (kind: AssetKind, id: string) => `${kind}:${id}`;
const digest = async (value: string) => sha256(value).toString();

/** Only literal media slots may be remapped. Queries, text, DOS and unknown properties stay exact. */
export function assetReferences(definition: StudioDefinition): Reference[] {
  const refs: Reference[] = [];
  const visit = (node: unknown, path: string[] = []) => {
    if (typeof node === 'string' && node.includes(`${assetType}://`)) {
      const slot = path.at(-1);
      if (!isNativeImage(node) || !['src','icon','svg'].includes(slot || '') || !['visualizations','layout','defaults'].includes(path[0])) throw new Error('This dashboard has an asset in an unsupported or dynamic slot. Keep its JSON and move that dependency in native Studio.');
      refs.push({path,id:node.slice(assetType.length+3),kind:slot==='icon'?'icon':'image'});
    } else if (typeof node==='string' && isPackagedImage(node) && ['src','icon','svg'].includes(path.at(-1)||'') && ['visualizations','layout','defaults'].includes(path[0])) {
      refs.push({path,id:'packaged_'+sha256(node).toString().slice(0,32),kind:path.at(-1)==='icon'?'icon':'image',packaged:node});
    } else if (node && typeof node === 'object') for (const [name,value] of Object.entries(node)) visit(value,[...path,name]);
  };
  visit(definition);
  if (new Set(refs.map(ref=>key(ref.kind,ref.id))).size > 16) throw new Error('Portable files support up to 16 shared assets.');
  return refs;
}
export async function exportPortable(definition: StudioDefinition, progress: (text: string)=>void, cancelled: ()=>boolean = ()=>false, includeReports = false, includeKnowledge = false): Promise<PortableDashboard> {
  if(cancelled())throw new Error('Export cancelled.');
  progress('Checking dashboard dependencies…');
  const prepared=await prepareDependencies(structuredClone(validateDefinition(definition)),includeReports,includeKnowledge);
  const snapshot = prepared.definition;
  const unique = new Map(assetReferences(snapshot).map(ref=>[key(ref.kind,ref.id),ref]));
  const assets: PortableAsset[] = [];
  for (const ref of unique.values()) {
    if (cancelled()) throw new Error('Export cancelled.');
    progress(`Reading asset ${assets.length+1} of ${unique.size}…`);
    const data = ref.packaged ? await readPackagedAsset(ref.packaged,ref.kind) : await readAssetData(ref.id,ref.kind);
    if (assetReferences(snapshot).some(other=>other.kind===ref.kind&&other.id===ref.id&&other.path.at(-1)==='svg')) svgAreaIds(data.dataURI);
    assets.push({...data,id:ref.id,kind:ref.kind,sha256:await digest(data.dataURI)});
    if (assets.reduce((sum,a)=>sum+a.dataURI.length,0) > 16_000_000) throw new Error('The combined assets exceed the 12 MB portable limit.');
  }
  if (cancelled()) throw new Error('Export cancelled.');
  for (const ref of assetReferences(snapshot)) if(ref.packaged){let node:Record<string,unknown>=snapshot;for(const part of ref.path.slice(0,-1))node=node[part] as Record<string,unknown>;node[ref.path.at(-1)!]=`${assetType}://${ref.id}`;}
  return {format:'constellation-dashboard',version:3,definition:validateDefinition(snapshot),assets,dependencies:prepared.dependencies,notes:prepared.notes,lookups:prepared.lookups||[]};
}
export async function readPortable(value: unknown): Promise<PortableDashboard> {
  if (!value || typeof value !== 'object') throw new Error('Choose a portable Constellation dashboard.');
  const file = value as PortableDashboard;
  if (file.format !== 'constellation-dashboard' || ![1,2,3].includes(file.version) || !Array.isArray(file.assets) || file.assets.length > 16 || JSON.stringify(value).length > 18_000_000) throw new Error('Unsupported or oversized portable dashboard.');
  if(file.lookups!==undefined && (file.version!==3 || !Array.isArray(file.lookups)||file.lookups.length>8||JSON.stringify(file.lookups).length>3_000_000))throw new Error('Invalid or oversized portable lookups.');
  if(file.dependencies!==undefined && (!Array.isArray(file.dependencies)||file.dependencies.length>100))throw new Error('Invalid dependency receipts.');
  if(file.notes!==undefined && (!Array.isArray(file.notes)||file.notes.length>100||file.notes.some(note=>typeof note!=='string'||note.length>2000)))throw new Error('Invalid transfer notes.');
  const definition = validateDefinition(file.definition), refs = assetReferences(definition).filter(ref=>file.version>=2||!ref.packaged), expected = new Set(refs.map(ref=>key(ref.kind,ref.id)));
  if(refs.some(ref=>ref.packaged))throw new Error('The portable file has unbundled packaged media. Export it again with this version.');
  const found = new Set<string>();
  for (const a of file.assets) {
    if (!a || !['image','icon'].includes(a.kind) || typeof a.id !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(a.id) || typeof a.name !== 'string' || a.name.length > 200 || typeof a.dataURI !== 'string') throw new Error('Invalid portable asset record.');
    const id = key(a.kind,a.id);
    if (found.has(id) || !expected.has(id)) throw new Error('The portable file has duplicate or unrelated assets.');
    found.add(id);validateAssetData(a.dataURI,a.kind);
    if (refs.some(ref=>key(ref.kind,ref.id)===id && ref.path.at(-1)==='svg')) svgAreaIds(a.dataURI);
    if (await digest(a.dataURI) !== a.sha256) throw new Error('An asset checksum does not match. Export the dashboard again.');
  }
  if (found.size !== expected.size || file.assets.reduce((n,a)=>n+a.dataURI.length,0) > 16_000_000) throw new Error('The portable file has missing or oversized assets.');
  return {format:file.format,version:file.version,definition:structuredClone(definition),assets:file.assets.map(a=>({...a})),...(file.dependencies?{dependencies:structuredClone(file.dependencies)}:{}),...(file.notes?{notes:[...file.notes]}:{}),...(file.lookups?{lookups:structuredClone(file.lookups)}:{})};
}
export async function importPortable(file: PortableDashboard, progress: (text: string)=>void): Promise<StudioDefinition> {
  // Validate the entire file before the first mutation. Never auto-replay a POST or delete shared records.
  const checked = await readPortable(file), replacements = new Map<string,string>();
  let definition = structuredClone(checked.definition);
  const dependencies=await checkDependencies(checked.definition,checked.dependencies,checked.lookups);
  if(dependencies.blocked)throw new Error('Import stopped before uploading: '+dependencies.dependencies.filter(item=>item.status==='missing').map(item=>`${item.kind} ${item.name}: ${item.detail}`).join(' '));
  let completed = 0;
  try {
    if(checked.lookups?.length){progress('Copying private lookup dependencies…');definition=(await importDependencies(definition,checked.dependencies,checked.lookups)).definition;}
    for (const asset of checked.assets) {
      progress(`Uploading shared asset ${completed+1} of ${checked.assets.length}…`);
      const uploaded = await uploadAssetData(asset);
      replacements.set(key(asset.kind,asset.id),uploaded.id);completed++;
    }
  } catch (failure) {
    throw new Error(`${completed} shared assets verified before the import stopped. Other uploads or private lookup copies may have completed. Your draft is unchanged. Check Studio’s shared libraries and Settings > Lookups before importing again. ${failure instanceof Error?failure.message:''}`);
  }
  for (const ref of assetReferences(definition)) {
    if(ref.packaged)continue;
    let node: Record<string,unknown> = definition;
    for (const part of ref.path.slice(0,-1)) node = node[part] as Record<string,unknown>;
    node[ref.path.at(-1)!] = `${assetType}://${replacements.get(key(ref.kind,ref.id))}`;
  }
  return validateDefinition(definition);
}
