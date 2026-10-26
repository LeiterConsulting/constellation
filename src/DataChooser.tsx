import { useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import TextArea from '@splunk/react-ui/TextArea';
import { providerRequest } from './api';
import { previewRanges, type DataDiscovery, type DataProfile, type DataScope } from './data';
import { Actions, Muted } from './styles';

export default function DataChooser({ discovery, initial, initialGoal = '', onBuild, onClose, returnFocus }: {
  discovery: DataDiscovery | null; initial?: DataScope | null; initialGoal?: string;
  onBuild: (scope: DataScope, prompt: string) => Promise<void>; onClose: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [mode, setMode] = useState(initial && 'query' in initial ? 'query' : 'index');
  const [scope, setScope] = useState<DataScope>(initial || { index: discovery?.activity[0]?.index || discovery?.indexes[0]?.name || '', earliest: '-24h', language: 'spl' });
  const [goal, setGoal] = useState(initialGoal);
  const [profile, setProfile] = useState<DataProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<'inspect' | 'build'>('inspect');
  const [error, setError] = useState('');
  const generation = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => { generation.current++; pending.current?.abort(); }, []);
  const stopInspection = () => { generation.current++; pending.current?.abort(); pending.current = null; setBusy(false); };
  const close = () => { stopInspection(); onClose(); };
  const change = (next: DataScope) => { generation.current++; setScope(next); setProfile(null); setError(''); };
  const chosen = (): DataScope => mode === 'query' ? { query: scope.query || '', language: scope.language || 'spl', earliest: scope.earliest }
    : { index: scope.index || '', sourcetype: scope.sourcetype || '', language: 'spl', earliest: scope.earliest };
  const inspect = async (build = false) => {
    const controller = new AbortController(); pending.current?.abort(); pending.current = controller;
    const turn = ++generation.current; setBusy(true); setStage(build && profile ? 'build' : 'inspect'); setError('');
    try {
      // Scope changes invalidate profile. Authoring still profiles server-side;
      // avoid repeating the same UI inspection when Build follows Inspect.
      const result = build && profile ? profile : await providerRequest<DataProfile>('profile', { ...chosen() }, controller.signal);
      if (turn !== generation.current) return;
      setProfile(result);
      if (!result.sampledRows) { setError('No rows found in this time range. Choose another dataset or range.'); return; }
      if (build) {
        setStage('build');
        const request = goal.trim() || 'Build a useful dashboard from this selected Splunk data. Show event volume over time and the most useful breakdowns justified by its verified fields. Use actual searches and no illustrative data.';
        await onBuild(result.scope, request); onClose();
      }
    } catch (failure) { if (turn === generation.current) setError(failure instanceof Error ? failure.message : 'Data could not be inspected.'); }
    finally { if (turn === generation.current) { pending.current = null; setBusy(false); } }
  };
  const sourcetypes = [...new Set(discovery?.activity.filter(item => item.index === scope.index).map(item => item.sourcetype) || [])];
  return <Modal open onRequestClose={close} returnFocus={returnFocus} style={{ width: 'min(700px, calc(100vw - 32px))' }}>
    <Modal.Header title="Build with Splunk data"/>
    <Modal.Body>
      <Muted>Searches use your Splunk permissions. Only field metadata goes to the model; event values stay in Splunk and the preview.</Muted>
      <ControlGroup label="Start from"><Select value={mode} disabled={busy} onChange={(_event, { value }) => { setMode(String(value)); setProfile(null); }}>
        <Select.Option label="An index in this instance" value="index"/><Select.Option label="My existing search" value="query"/>
      </Select></ControlGroup>
      {mode === 'index' ? <>
        {!discovery?.indexes.length ? <Message type="info">No index catalog is available. Choose “My existing search” above, or close and reopen after discovery finishes.</Message> : null}
        <ControlGroup label="Index"><Select value={scope.index || ''} disabled={busy} filter onChange={(_event, { value }) => change({ ...scope, index: String(value), sourcetype: '' })}>
          {(discovery?.indexes || []).map(item => <Select.Option key={item.name} value={item.name} label={item.name}/>)}</Select></ControlGroup>
        <ControlGroup label="Sourcetype"><Select value={scope.sourcetype || ''} disabled={busy} onChange={(_event, { value }) => change({ ...scope, sourcetype: String(value) })}>
          <Select.Option value="" label="All sourcetypes"/>{sourcetypes.map(name => <Select.Option key={name} value={name} label={name}/>)}</Select></ControlGroup>
      </> : <>
        <ControlGroup label="Search language"><Select value={scope.language || 'spl'} disabled={busy} onChange={(_event, { value }) => change({ ...scope, language: value as 'spl' | 'spl2' })}>
          <Select.Option value="spl" label="SPL"/><Select.Option value="spl2" label="SPL2"/></Select></ControlGroup>
        <ControlGroup label="Existing search"><TextArea value={scope.query || ''} disabled={busy} rowsMin={3} onChange={(_event, { value }) => change({ ...scope, query: value })}/></ControlGroup>
      </>}
      <ControlGroup label="Time range"><Select value={scope.earliest} disabled={busy} onChange={(_event, { value }) => change({ ...scope, earliest: value as DataScope['earliest'] })}>
        {previewRanges.map(range => <Select.Option key={range.value} {...range}/>)}</Select></ControlGroup>
      <ControlGroup label="What should this dashboard help you understand?"><TextArea value={goal} disabled={busy} onChange={(_event, { value }) => setGoal(value)} rowsMin={2}/></ControlGroup>
      {profile ? <><Muted role="status">Found {profile.fields.length} fields in a bounded sample of {profile.sampledRows} rows.{profile.completion?.state === 'partial' ? ' This sample is partial; it does not establish complete counts.' : ''}</Muted>
        <details><summary>Field details</summary><Muted>{profile.fields.map(field => field.name).join(', ')}. This sample does not establish a business definition or complete coverage.</Muted></details></> : null}
      {error ? <Message type="error">{error}</Message> : null}
      {busy ? <Muted role="status">{stage === 'build' ? 'Building your dashboard…' : 'Inspecting the selected data…'}</Muted> : null}
    </Modal.Body><Modal.Footer><Actions><Button onClick={busy ? stopInspection : close}>{busy ? 'Stop inspection' : 'Cancel'}</Button><Button onClick={() => void inspect()} disabled={busy}>Inspect fields</Button>
      <Button appearance="primary" onClick={() => void inspect(true)} disabled={busy || (mode === 'index' ? !scope.index : !scope.query?.trim())}>Build dashboard</Button></Actions></Modal.Footer>
  </Modal>;
}
