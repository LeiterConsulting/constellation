import { useState } from 'react';
import Modal from '@splunk/react-ui/Modal';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Select from '@splunk/react-ui/Select';
import Text from '@splunk/react-ui/Text';
import TextArea from '@splunk/react-ui/TextArea';
import Message from '@splunk/react-ui/Message';
import { pagesOf, type PagePurpose } from './pages';
import type { StudioDefinition } from './document';
import { Actions, Muted } from './styles';

export default function PageManager({definition,purposes,activeTab,onSave,onClose,returnFocus}:{
  definition:StudioDefinition;purposes:PagePurpose;activeTab?:string;
  onSave:(id:string,name:string,purpose:string)=>void;onClose:()=>void;returnFocus:React.RefObject<HTMLElement>;
}) {
  const pages=pagesOf(definition,purposes),first=pages.find(page=>page.id===activeTab)||pages[0];
  const [id,setId]=useState(first?.id||''),[name,setName]=useState(first?.name||''),[purpose,setPurpose]=useState(first?.purpose||''),[error,setError]=useState('');
  return <Modal open onRequestClose={onClose} returnFocus={returnFocus} style={{width:'min(620px, calc(100vw - 32px))'}}>
    <Modal.Header title="Pages"/><Modal.Body>
      <Muted>Give each page a clear name and purpose. The agent uses these when organizing charts and navigation.</Muted>
      <ControlGroup label="Page"><Select value={id} onChange={(_event,{value})=>{const page=pages.find(page=>page.id===value);setId(String(value));setName(page?.name||'');setPurpose(page?.purpose||'');setError('');}}>
        {pages.map(page=><Select.Option key={page.id} value={page.id} label={page.name}/>)}<Select.Option value="" label="New page"/>
      </Select></ControlGroup>
      <ControlGroup label="Page name"><Text value={name} onChange={(_event,{value})=>setName(value)}/></ControlGroup>
      <ControlGroup label="Page purpose"><TextArea value={purpose} rowsMin={2} rowsMax={5} onChange={(_event,{value})=>setPurpose(value)}/></ControlGroup>
      {error?<Message type="error">{error}</Message>:null}
    </Modal.Body><Modal.Footer><Actions><Button onClick={onClose}>Cancel</Button><Button appearance="primary" disabled={!name.trim()||purpose.length>1200} onClick={()=>{
      try{onSave(id || `layout_${crypto.getRandomValues(new Uint32Array(1))[0].toString(16)}`,name,purpose);onClose();}catch(failure){setError(failure instanceof Error?failure.message:'The page could not be updated.');}
    }}>Save page</Button></Actions></Modal.Footer>
  </Modal>;
}
