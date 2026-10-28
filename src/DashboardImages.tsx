import { useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import { listDashboardAssets, uploadDashboardAsset, type DashboardAsset } from './dashboardAssets';
import { Actions, Muted } from './styles';

export default function DashboardImages({ onChoose, onClose, returnFocus }: {
  onChoose: (asset: DashboardAsset) => void; onClose: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [assets,setAssets] = useState<DashboardAsset[]>([]), [selected,setSelected] = useState('');
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [file,setFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null), mounted = useRef(true);
  useEffect(() => { mounted.current=true; void listDashboardAssets().then(items => { if(mounted.current) setAssets(items); }).catch(() => { if(mounted.current) setError('The shared image list could not be loaded.'); }); return () => { mounted.current=false; }; }, []);
  return <Modal open returnFocus={returnFocus} onRequestClose={() => { if(!busy)onClose(); }} style={{width:'min(560px, calc(100vw - 32px))'}}>
    <Modal.Header title="Dashboard images"/><Modal.Body>
      <Muted>Images in Studio’s library are shared with other Splunk users, including images on private dashboards. They stay in this Splunk instance and are not sent to your AI provider.</Muted>
      <ControlGroup label="Shared image" help="First 100 images. Reusing an image keeps the same native Studio reference."><Select filter disabled={busy} value={selected} onChange={(_event,{value})=>setSelected(String(value))}>
        {assets.map(asset=><Select.Option key={asset.id} value={asset.id} label={asset.name}/>)}</Select></ControlGroup>
      <Actions><Button disabled={busy} onClick={()=>input.current?.click()}>Choose image to upload</Button>{file?<Muted>{file.name}</Muted>:null}</Actions>
      <input ref={input} hidden type="file" aria-label="Choose dashboard image" accept="image/png,image/jpeg,image/webp,image/gif" onChange={event=>{setFile(event.target.files?.[0]||null);event.target.value='';setError('');}}/>
      {file?<Button disabled={busy} onClick={()=>{setBusy(true);setError('');void uploadDashboardAsset(file).then(asset=>{if(mounted.current){setAssets(items=>[asset,...items]);setSelected(asset.id);setFile(null);}}).catch(failure=>{if(mounted.current)setError(failure instanceof Error?failure.message:'The upload could not be verified.');}).finally(()=>{if(mounted.current)setBusy(false);});}}>Upload shared image</Button>:null}
      <Muted>PNG, JPEG, GIF or WebP · 4 MB maximum. Your native Studio permissions apply. Uploaded images are separate from sketch/PDF references attached to chat.</Muted>
      {busy?<Muted role="status">Uploading shared image…</Muted>:null}{error?<Message type="error">{error}</Message>:null}
    </Modal.Body><Modal.Footer><Button disabled={busy} onClick={onClose}>Close</Button><Button appearance="primary" disabled={busy||!selected} onClick={()=>{const asset=assets.find(item=>item.id===selected);if(asset) { try { onChoose(asset); } catch(failure) { setError(failure instanceof Error ? failure.message : 'The image could not be placed.'); } }}}>Use image</Button></Modal.Footer>
  </Modal>;
}
