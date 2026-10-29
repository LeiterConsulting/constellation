import { useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import { listDashboardAssets, uploadDashboardAsset, readAssetData, type AssetKind, type DashboardAsset } from './dashboardAssets';
import { svgAreaIds } from './svgAssets';
import { Actions, Muted } from './styles';

export default function DashboardImages({ onChoose, onClose, returnFocus }: {
  onChoose: (asset: DashboardAsset) => void; onClose: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [library,setLibrary] = useState<'image'|'icon'|'map'>('image');
  const kind: AssetKind = library==='icon'?'icon':'image';
  const [assets,setAssets] = useState<DashboardAsset[]>([]), [selected,setSelected] = useState('');
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [file,setFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null), mounted = useRef(true);
  useEffect(() => { mounted.current=true; return () => { mounted.current=false; }; }, []);
  useEffect(() => {
    let current=true;
    void listDashboardAssets(kind).then(items => { if(current) setAssets(previous=>[...items,...previous.filter(item=>item.kind===kind&&!items.some(other=>other.id===item.id))]); })
      .catch(() => { if(current) setError('The shared asset list could not be loaded.'); });
    return () => { current=false; };
  }, [kind,library]);
  return <Modal open returnFocus={returnFocus} onRequestClose={() => { if(!busy)onClose(); }} style={{width:'min(560px, calc(100vw - 32px))'}}>
    <Modal.Header title="Images and icons"/><Modal.Body>
      <Muted>Images and icons in Studio’s libraries are shared with other Splunk users, including images on private dashboards. They stay in this Splunk instance and are not sent to your AI provider.</Muted>
      <ControlGroup label="Library"><Select disabled={busy} value={library} onChange={(_event,{value})=>{setLibrary(value as 'image'|'icon'|'map');setAssets([]);setSelected('');setError('');}}><Select.Option value="image" label="Images"/><Select.Option value="icon" label="SVG icons"/><Select.Option value="map" label="SVG choropleth maps"/></Select></ControlGroup>
      <ControlGroup label="Shared asset" help="First 100 assets. Reusing an asset keeps the same native Studio reference."><Select filter disabled={busy} value={selected} onChange={(_event,{value})=>setSelected(String(value))}>
        {assets.map(asset=><Select.Option key={asset.id} value={asset.id} label={asset.name}/>)}</Select></ControlGroup>
      <Actions><Button disabled={busy} onClick={()=>input.current?.click()}>Choose file to upload</Button>{file?<Muted>{file.name}</Muted>:null}</Actions>
      <input ref={input} hidden type="file" aria-label="Choose dashboard asset" accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,.svg" onChange={event=>{setFile(event.target.files?.[0]||null);event.target.value='';setError('');}}/>
      {file?<Button disabled={busy} onClick={()=>{setBusy(true);setError('');void uploadDashboardAsset(file,library==='map'?'map':undefined).then(asset=>{if(mounted.current){if(asset.kind!==kind){setLibrary(asset.kind||'image');}setAssets(items=>[asset,...items]);setSelected(asset.id);setFile(null);}}).catch(failure=>{if(mounted.current)setError(failure instanceof Error?failure.message:'The upload could not be verified.');}).finally(()=>{if(mounted.current)setBusy(false);});}}>Upload shared asset</Button>:null}
      <Muted>PNG, JPEG, GIF or WebP · 4 MB maximum. SVG icons · 500 KB; SVG maps · 250 KB with unique path IDs. Passive shapes and local gradients only. Select SVG choropleth maps before uploading a map. Area IDs may inform the agent; artwork bytes stay in Splunk. Your native Studio permissions apply. Uploaded images are separate from sketch/PDF references attached to chat.</Muted>
      {busy?<Muted role="status">Uploading and checking shared asset…</Muted>:null}{error?<Message type="error">{error}</Message>:null}
    </Modal.Body><Modal.Footer><Button disabled={busy} onClick={onClose}>Close</Button><Button appearance="primary" disabled={busy||!selected} onClick={()=>{const asset=assets.find(item=>item.id===selected);if(!asset)return;setBusy(true);void (async()=>{if(library==='map'){const data=await readAssetData(asset.id,'image');svgAreaIds(data.dataURI);}onChoose({...asset,usage:library==='map'?'map':undefined});})().catch(failure=>setError(failure instanceof Error?failure.message:'The asset could not be placed.')).finally(()=>{if(mounted.current)setBusy(false);});}}>Use asset</Button></Modal.Footer>
  </Modal>;
}
