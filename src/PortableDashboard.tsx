import { useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Switch from '@splunk/react-ui/Switch';
import { checkDependencies, type DependencyCheck } from './dashboardDependencies';
import type { StudioDefinition } from './document';
import { exportPortable, importPortable, type PortableDashboard as PortableFile } from './portableAssets';
import { Muted } from './styles';

export default function PortableDashboard({ definition, file, onImport, onClose, returnFocus }: {
  definition: StudioDefinition; file?: PortableFile; onImport: (definition: StudioDefinition)=>Promise<boolean>;
  onClose: ()=>void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [progress,setProgress] = useState('');
  const [attempted,setAttempted] = useState(false), [result,setResult] = useState<StudioDefinition>();
  const [includeReports,setIncludeReports] = useState(false), [check,setCheck] = useState<DependencyCheck>();
  const [checking,setChecking] = useState(!!file), [checkAttempt,setCheckAttempt] = useState(0);
  const hasReports = Object.values(definition.dataSources || {}).some(source=>source.type==='ds.savedSearch');
  const cancelled = useRef(false);
  useEffect(()=>()=>{cancelled.current=true;},[]);
  useEffect(()=>{
    if(!file)return;let current=true;setChecking(true);setError('');setCheck(undefined);
    void checkDependencies(file.definition,file.dependencies).then(value=>{if(current)setCheck(value);})
      .catch(failure=>{if(current)setError(failure instanceof Error?failure.message:'Dependencies could not be checked.');})
      .finally(()=>{if(current)setChecking(false);});
    return ()=>{current=false;};
  },[file,checkAttempt]);
  const run = async () => {
    setBusy(true);setError('');cancelled.current=false;
    try {
      if (file) {
        setAttempted(true);
        const next = result || await importPortable(file,setProgress);
        setResult(next);if(!await onImport(next))throw new Error('Save the current draft before opening the imported dashboard. Its uploaded assets are retained; use Open imported draft to continue.');onClose();
      } else {
        const bundle = await exportPortable(definition,setProgress,()=>cancelled.current,includeReports);
        const url = URL.createObjectURL(new Blob([JSON.stringify(bundle)],{type:'application/json'}));
        const link = document.createElement('a');link.href=url;link.download='constellation-dashboard.portable.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        setProgress('Portable dashboard downloaded.');
      }
    } catch (failure) { setError(failure instanceof Error?failure.message:'The asset transfer could not be verified.'); }
    finally {setBusy(false);}
  };
  return <Modal open returnFocus={returnFocus} onRequestClose={()=>{if(!busy)onClose();}} style={{width:'min(560px, calc(100vw - 32px))'}}>
    <Modal.Header title={file?'Import dashboard with assets':'Export dashboard with assets'}/><Modal.Body>
      {file?<><p><strong>{file.definition.title || 'Untitled dashboard'}</strong> · {file.assets.length} shared assets</p>
        <Message type="warning">Import uploads these images and icons to this instance’s shared Studio libraries. Other Splunk users can read them, even if your dashboard is private. Your native upload permissions apply.</Message>
        <Muted>{file.assets.map(asset=>`${asset.name} (${asset.kind})`).join(', ') || 'No shared uploads needed.'}</Muted>
        {checking?<Muted role="status">Checking destination dependencies…</Muted>:null}
        {check?<details open={check.blocked}><summary>{check.blocked?'Dependencies need attention':`${check.dependencies.length} destination dependencies checked`}</summary>
          {check.dependencies.map(item=><p key={`${item.kind}:${item.app}:${item.name}`}><strong>{item.kind}: {item.name}</strong> · {item.status}<br/>{item.detail}</p>)}</details>:null}
        {file.notes?.map(note=><Muted key={note}>{note}</Muted>)}
        {!checking?<Button disabled={busy} onClick={()=>setCheckAttempt(value=>value+1)}>Check again</Button>:null}
      </>:<><Muted>Download this Studio definition with supported shared and packaged images, SVG icons and choropleth maps. Keep the file private if its searches or artwork are sensitive.</Muted>
        {hasReports?<><Switch appearance="checkbox" selected={includeReports} disabled={busy} onClick={()=>setIncludeReports(value=>!value)}>Include compatible report searches</Switch>
          <Muted>Rerun these reports as the dashboard viewer. Schedules, cached results and report-owner permissions are not copied. Check app-specific field extraction on the destination.</Muted></>:null}</>}
      <Muted>Indexes, lookups, macros, custom visualizations and modules still need destination access/configuration. Their contents and external media are not copied. Conversations and provider settings are excluded.</Muted>
      {progress?<Muted role="status">{progress}</Muted>:null}{error?<Message type="error">{error}</Message>:null}
    </Modal.Body><Modal.Footer><Button disabled={busy&&!!file} onClick={()=>{if(busy)cancelled.current=true;else onClose();}}>{busy&&!file?'Cancel export':'Close'}</Button>
      <Button appearance="primary" disabled={busy || !!file&&(checking||!check||check.blocked||attempted&&!result)} onClick={()=>void run()}>{file?(result?'Open imported draft':'Upload shared assets and import'):'Download with assets'}</Button>
    </Modal.Footer>
  </Modal>;
}
