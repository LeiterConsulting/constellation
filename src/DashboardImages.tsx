import { useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import { listDashboardAssets, uploadDashboardAsset, type AssetKind, type DashboardAsset } from './dashboardAssets';
import { Actions, Muted } from './styles';

export default function DashboardImages({ onChoose, onClose, returnFocus }: {
  onChoose: (asset: DashboardAsset) => void; onClose: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [kind,setKind] = useState<AssetKind>('image');
  const [assets,setAssets] = useState<DashboardAsset[]>([]), [selected,setSelected] = useState('');
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [file,setFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null), mounted = useRef(true);
  useEffect(() => { mounted.current=true; return () => { mounted.current=false; }; }, []);
  useEffect(() => {
    let current=true;
    void listDashboardAssets(kind).then(items => { if(current) setAssets(previous=>[...items,...previous.filter(item=>item.kind===kind&&!items.some(other=>other.id===item.id))]); })
      .catch(() => { if(current) setError('The shared asset list could not be loaded.'); });
    return () => { current=false; };
  }, [kind]);
  return <Modal open returnFocus={returnFocus} onRequestClose={() => { if(!busy)onClose(); }} style={{width:'min(560px, calc(100vw - 32px))'}}>
    <Modal.Header title="Images and icons"/><Modal.Body>
      <Muted>Images and icons in Studio’s libraries are shared with other Splunk users, including images on private dashboards. They stay in this Splunk instance and are not sent to your AI provider.</Muted>
      <ControlGroup label="Library"><Select disabled={busy} value={kind} onChange={(_event,{value})=>{setKind(value as AssetKind);setAssets([]);setSelected('');setError('');}}><Select.Option value="image" label="Images"/><Select.Option value="icon" label="SVG icons"/></Select></ControlGroup>
      <ControlGroup label="Shared asset" help="First 100 assets. Reusing an asset keeps the same native Studio reference."><Select filter disabled={busy} value={selected} onChange={(_event,{value})=>setSelected(String(value))}>
        {assets.map(asset=><Select.Option key={asset.id} value={asset.id} label={asset.name}/>)}</Select></ControlGroup>
      <Actions><Button disabled={busy} onClick={()=>input.current?.click()}>Choose file to upload</Button>{file?<Muted>{file.name}</Muted>:null}</Actions>
      <input ref={input} hidden type="file" aria-label="Choose dashboard asset" accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,.svg" onChange={event=>{setFile(event.target.files?.[0]||null);event.target.value='';setError('');}}/>
      {file?<Button disabled={busy} onClick={()=>{setBusy(true);setError('');void uploadDashboardAsset(file).then(asset=>{if(mounted.current){if(asset.kind!==kind){setKind(asset.kind||'image');}setAssets(items=>[asset,...items]);setSelected(asset.id);setFile(null);}}).catch(failure=>{if(mounted.current)setError(failure instanceof Error?failure.message:'The upload could not be verified.');}).finally(()=>{if(mounted.current)setBusy(false);});}}>Upload shared asset</Button>:null}
      <Muted>PNG, JPEG, GIF or WebP · 4 MB maximum. SVG icons · 500 KB, passive paths/shapes and local gradients only. Your native Studio permissions apply. Uploaded images are separate from sketch/PDF references attached to chat.</Muted>
      {busy?<Muted role="status">Uploading and checking shared asset…</Muted>:null}{error?<Message type="error">{error}</Message>:null}
    </Modal.Body><Modal.Footer><Button disabled={busy} onClick={onClose}>Close</Button><Button appearance="primary" disabled={busy||!selected} onClick={()=>{const asset=assets.find(item=>item.id===selected);if(asset) { try { onChoose(asset); } catch(failure) { setError(failure instanceof Error ? failure.message : 'The image could not be placed.'); } }}}>Use asset</Button></Modal.Footer>
  </Modal>;
}
