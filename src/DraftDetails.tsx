import { useEffect, useState } from 'react';
import Modal from '@splunk/react-ui/Modal';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import TextArea from '@splunk/react-ui/TextArea';
import Message from '@splunk/react-ui/Message';
import { providerRequest, isSplunk } from './api';
import type { DashboardBrief } from './drafts';
import { Actions, Muted } from './styles';

interface RevisionSummary { version: number; title: string; updatedAt: string; }
export default function DraftDetails({ id, brief, scope, onSave, onRestore, onClose, returnFocus }: {
  id: string; brief: DashboardBrief; scope: string; onSave: (brief: DashboardBrief) => void;
  onRestore: (version: number) => Promise<void>; onClose: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [tab, setTab] = useState<'brief' | 'history'>('brief');
  const [value, setValue] = useState(brief);
  const [items, setItems] = useState<RevisionSummary[]>([]);
  const [restoring, setRestoring] = useState(false);
  const [loading, setLoading] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    if (tab !== 'history' || !isSplunk()) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true); setError('');
    void providerRequest<{ revisions: RevisionSummary[] }>('drafts', { action: 'history', id }, controller.signal)
      .then(result => { if (!controller.signal.aborted) setItems(result.revisions); })
      .catch(failure => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'History is unavailable.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [tab, id]);
  return <Modal open onRequestClose={() => { if (!restoring) onClose(); }} returnFocus={returnFocus} style={{ width: 'min(640px, calc(100vw - 32px))' }}>
    <Modal.Header title="Draft details"/><Modal.Body>
      <Actions><Button disabled={restoring} aria-pressed={tab === 'brief'} onClick={() => setTab('brief')}>Brief</Button><Button aria-pressed={tab === 'history'} disabled={!isSplunk() || restoring} onClick={() => setTab('history')}>Version history</Button></Actions>
      {tab === 'brief' ? <>
        <Muted>The agent keeps this brief across conversations and sessions. Edit it when your requirements change.</Muted>
        <ControlGroup label="Purpose and audience"><TextArea value={value.purpose} rowsMin={3} rowsMax={6} onChange={(_event, { value: purpose }) => setValue(previous => ({ ...previous, purpose }))}/></ControlGroup>
        <ControlGroup label="Requirements, units and exclusions"><TextArea value={value.requirements} rowsMin={3} rowsMax={6} onChange={(_event, { value: requirements }) => setValue(previous => ({ ...previous, requirements }))}/></ControlGroup>
        <Muted>{scope || 'Choose Splunk data to establish the search scope.'} Page names and purposes are managed in Pages.</Muted>
      </> : <>
        <Muted>Up to 10 previous dashboard versions are kept within a 4 MB history budget. Restoring keeps your current conversation and saves the version you leave behind.</Muted>
        {loading || restoring ? <Muted role="status">Loading or restoring history…</Muted> : !items.length ? <Muted>No previous dashboard changes yet.</Muted> : <ul>{items.map(item => <li key={item.version}>
          <p>{item.title} · {new Date(item.updatedAt).toLocaleString()}</p>
          <Button disabled={restoring} onClick={() => { setRestoring(true); setError(''); void onRestore(item.version).then(onClose).catch(failure => { setError(failure instanceof Error ? failure.message : 'This version could not be restored.'); setRestoring(false); }); }}>Restore version {item.version}</Button>
        </li>)}</ul>}
      </>}
      {error ? <Message type="error">{error}</Message> : null}
    </Modal.Body><Modal.Footer><Button disabled={restoring} onClick={onClose}>Close</Button>{tab === 'brief' ? <Button appearance="primary" disabled={restoring || value.purpose.length > 8000 || value.requirements.length > 8000} onClick={() => { onSave(value); onClose(); }}>Save brief</Button> : null}</Modal.Footer>
  </Modal>;
}
