import { useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Text from '@splunk/react-ui/Text';
import Link from '@splunk/react-ui/Link';
import { isSplunk, listDashboards, providerRequest } from './api';
import { openDraft, type DraftList, type DraftRecord, type DraftSummary } from './drafts';
import { Actions, LibraryRow, Muted } from './styles';

type NativeEntry = Awaited<ReturnType<typeof listDashboards>>[number];
export default function DashboardLibrary({ onClose, onOpen, onNative, onUpdated, onDeleted, onImport, onExample, returnFocus }: {
  onClose: () => void; onOpen: (record: DraftRecord) => void; onNative: (item: NativeEntry) => void;
  onUpdated: (record: DraftRecord) => void; onDeleted: (id: string) => void;
  onImport: () => void; onExample: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [list, setList] = useState<DraftList>({ drafts: [], trash: [], activeId: null });
  const [native, setNative] = useState<NativeEntry[]>([]);
  const [filter, setFilter] = useState('');
  const filterInput = useRef<HTMLInputElement>(null);
  const [trash, setTrash] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [renaming, setRenaming] = useState<{ kind: 'draft' | 'native'; id: string; version?: number; title: string } | null>(null);
  const refresh = async () => {
    if (!isSplunk()) return;
    const results = await Promise.allSettled([providerRequest<DraftList>('drafts'), listDashboards()]);
    if (results[0].status === 'fulfilled') setList(results[0].value);
    if (results[1].status === 'fulfilled') setNative(results[1].value);
    for (const result of results) if (result.status === 'rejected') throw result.reason;
  };
  useEffect(() => {
    let current = true;
    if (isSplunk()) {
      setBusy(true);
      void Promise.allSettled([providerRequest<DraftList>('drafts'), listDashboards()]).then(results => {
        if (!current) return;
        if (results[0].status === 'fulfilled') setList(results[0].value); else setError('Your draft list could not be loaded. Refresh to retry.');
        if (results[1].status === 'fulfilled') setNative(results[1].value); else setError('Saved Studio views could not be loaded. Your current draft is preserved.');
      }).finally(() => { if (current) setBusy(false); });
    }
    return () => { current = false; };
  }, []);
  const perform = async (work: () => Promise<void>) => {
    setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (failure) { setError(failure instanceof Error ? failure.message : 'This action could not be completed.'); }
    finally { setBusy(false); }
  };
  const draftAction = (item: DraftSummary, action: string, title?: string) => perform(async () => {
    const record = await providerRequest<DraftRecord>('drafts', { action, id: item.id, version: item.version, title });
    if (action === 'duplicate') { onOpen(record); return; }
    if (action === 'delete') { onDeleted(item.id); setNotice('Draft moved to Trash. Its conversation is retained.'); }
    if (action === 'rename') { onUpdated(record); setRenaming(null); requestAnimationFrame(() => filterInput.current?.focus()); }
    await refresh();
  });
  const nativeAction = (item: NativeEntry, action: string, title?: string) => perform(async () => {
    const record = await providerRequest<DraftRecord>('library', { action, name: item.name, title });
    if (action === 'duplicate') { onOpen(record); return; }
    setRenaming(null); await refresh(); requestAnimationFrame(() => filterInput.current?.focus());
    setNotice(action === 'delete' ? 'Saved dashboard moved to Trash. You can restore its original Studio view.' : 'Saved dashboard renamed.');
  });
  const matching = (title: string) => title.toLowerCase().includes(filter.trim().toLowerCase());
  const renameEditor = (kind: 'draft' | 'native', id: string) => renaming?.id === id && renaming.kind === kind ? <Actions>
    <ControlGroup label="Dashboard title"><Text value={renaming.title} disabled={busy} onChange={(_event, { value }) => setRenaming({ ...renaming, title: value })}/></ControlGroup>
    <Button disabled={busy || !renaming.title.trim()} onClick={() => {
      if (kind === 'draft') { const item = list.drafts.find(row => row.id === id); if (item) void draftAction(item, 'rename', renaming.title); }
      else { const item = native.find(row => row.name === id); if (item) void nativeAction(item, 'rename', renaming.title); }
    }}>Save title</Button><Button disabled={busy} onClick={() => setRenaming(null)}>Cancel rename</Button>
  </Actions> : null;
  return <Modal open onRequestClose={() => { if (!busy) onClose(); }} returnFocus={returnFocus} style={{ width: 'min(850px, calc(100vw - 32px))' }}>
    <Modal.Header title="Dashboards"/><Modal.Body>
      <Actions><Button aria-pressed={!trash} appearance={trash ? 'secondary' : 'primary'} onClick={() => setTrash(false)}>My dashboards</Button><Button aria-pressed={trash} appearance={trash ? 'primary' : 'secondary'} onClick={() => setTrash(true)}>Trash</Button>
        <Button onClick={() => void perform(refresh)} disabled={busy || !isSplunk()}>Refresh list</Button></Actions>
      <ControlGroup label="Find a dashboard"><Text inputRef={filterInput} value={filter} onChange={(_event, { value }) => setFilter(value)}/></ControlGroup>
      {error ? <Message type="error">{error}</Message> : null}{notice ? <Message type="success">{notice}</Message> : null}
      {busy ? <Muted role="status">Updating dashboards…</Muted> : null}
      {trash ? <>
        <Muted>Deleted drafts retain their conversations. Deleted private Studio views retain a restore copy in this app.</Muted>
        {list.trash.filter(item => matching(item.title)).map(item => <LibraryRow key={item.id}><div><strong>{item.title}</strong><Muted>{item.kind === 'native_backup' ? 'Saved Studio dashboard' : 'Draft and conversation'}</Muted></div>
          <Button disabled={busy} aria-label={`Restore ${item.title}`} onClick={() => void perform(async () => {
            if (item.kind === 'native_backup') await providerRequest('library', { action: 'restore', id: item.id, version: item.version });
            else await providerRequest('drafts', { action: 'restore', id: item.id, version: item.version });
            await refresh(); setNotice('Dashboard restored.');
          })}>Restore</Button></LibraryRow>)}
        {!busy && (!list.trash.length ? <Muted>Trash is empty.</Muted> : !list.trash.some(item => matching(item.title)) ? <Muted>No deleted dashboards match your search.</Muted> : null)}
      </> : <>
        <Muted>Drafts save privately in Splunk with their conversations and data context.</Muted>
        {list.drafts.filter(item => matching(item.title)).map(item => <LibraryRow key={item.id}><div>
          <Button appearance="subtle" disabled={busy} onClick={() => void perform(async () => onOpen(await openDraft(item.id)))}>{item.title}</Button>
          <Muted>Draft · {new Date(item.updatedAt).toLocaleString()}</Muted></div><Actions>
          <Button disabled={busy} aria-label={`Rename draft ${item.title}`} onClick={() => setRenaming({ kind: 'draft', id: item.id, title: item.title, version: item.version })}>Rename</Button>
          <Button disabled={busy} aria-label={`Duplicate draft ${item.title}`} onClick={() => void draftAction(item, 'duplicate')}>Duplicate</Button>
          <Button disabled={busy} aria-label={`Delete draft ${item.title}`} onClick={() => void draftAction(item, 'delete')}>Delete</Button>
        </Actions>{renameEditor('draft', item.id)}</LibraryRow>)}
        {!busy && !list.drafts.some(item => matching(item.title)) ? <Muted>{filter.trim() ? 'No drafts match your search.' : 'No drafts yet. Start a new dashboard or import Studio JSON.'}</Muted> : null}
        <Muted>Studio dashboards in Constellation. Copies saved to other apps appear in those apps’ dashboard lists.</Muted>
        {native.filter(item => matching(item.title)).map(item => <LibraryRow key={item.name}><div><Button appearance="subtle" disabled={busy} onClick={() => void perform(async () => onNative(item))}>{item.title}</Button><Muted>{item.canManage ? 'Private Studio dashboard' : 'Shared Studio dashboard · open or duplicate'}</Muted></div><Actions>
          <Link to={item.url} openInNewContext>Open in Studio</Link>
          {item.canManage ? <Button disabled={busy} aria-label={`Rename saved ${item.title}`} onClick={() => setRenaming({ kind: 'native', id: item.name, title: item.title })}>Rename</Button> : null}
          <Button disabled={busy} aria-label={`Duplicate saved ${item.title}`} onClick={() => void nativeAction(item, 'duplicate')}>Duplicate</Button>
          {item.canManage ? <Button disabled={busy} aria-label={`Delete saved ${item.title}`} onClick={() => void nativeAction(item, 'delete')}>Delete</Button> : null}
        </Actions>{renameEditor('native', item.name)}</LibraryRow>)}
        {!busy && !native.some(item => matching(item.title)) ? <Muted>{filter.trim() ? 'No Studio dashboards match your search.' : 'No Studio dashboards saved in this app yet.'}</Muted> : null}
        <Actions><Button disabled={busy} onClick={onImport}>Import dashboard file</Button><Button disabled={busy} onClick={onExample}>Open example dashboard</Button></Actions><Muted>Import Studio JSON or a Constellation portable file. The example contains illustrative data.</Muted>
      </>}
    </Modal.Body><Modal.Footer><Button disabled={busy} onClick={onClose}>Close</Button></Modal.Footer>
  </Modal>;
}
