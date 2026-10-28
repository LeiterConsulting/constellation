import { useEffect, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Link from '@splunk/react-ui/Link';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import { listDestinationApps, saveCopy } from './api';
import type { StudioDefinition } from './document';
import { hasSharedImages } from './dashboardAssets';
import { Muted } from './styles';

export default function SaveDashboard({ definition, theme, onSaved, onClose, returnFocus }: {
  definition: StudioDefinition; theme: 'light' | 'dark';
  onSaved: (result: { name: string; url: string }) => void; onClose: () => void; returnFocus: React.RefObject<HTMLElement>;
}) {
  const [apps, setApps] = useState([{ name: 'constellation', label: 'Constellation' }]);
  const [app, setApp] = useState('constellation');
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [result, setResult] = useState<{ name: string; url: string } | null>(null);
  useEffect(() => {
    let current = true;
    void listDestinationApps().then(items => { if (current) setApps(items.some(item => item.name === 'constellation') ? items : [...apps, ...items]); })
      .catch(() => { if (current) setError('The app list could not be loaded. You can still save in Constellation.'); });
    return () => { current = false; };
  }, []);
  return <Modal open onRequestClose={() => { if (!busy) onClose(); }} returnFocus={returnFocus} style={{ width: 'min(560px, calc(100vw - 32px))' }}>
    <Modal.Header title={result ? 'Dashboard saved' : 'Save to Splunk'}/><Modal.Body>
      {error ? <Message type="error">{error}</Message> : null}
      {result ? <><Message type="success">Saved a private Studio dashboard and verified its definition.</Message>
        <Muted>Use Actions → Edit permissions in Studio when you are ready to share it. Viewers need access to its data and referenced knowledge objects.</Muted>
        <Link to={result.url} openInNewContext appearance="standalone">Open dashboard in Studio</Link>
      </> : <>
        <p><strong>{definition.title || 'Untitled dashboard'}</strong></p>
        <ControlGroup label="Destination app" help="The dashboard runs in this app’s search context. Splunk checks your permission to create it.">
          <Select value={app} disabled={busy} filter onChange={(_event, { value }) => setApp(String(value))}>
            {apps.map(item => <Select.Option key={item.name} value={item.name} label={item.label}/>)}</Select>
        </ControlGroup>
        <Muted>This creates a new private Dashboard Studio copy. Your working draft and conversation stay in Constellation. Existing dashboards are never overwritten.</Muted>
        {hasSharedImages(definition) ? <Message type="info">This dashboard uses shared Studio images or icons stored in this Splunk instance. Sharing the dashboard keeps those references. JSON exports and app packages do not contain uploaded files. Use More → Export with assets to move supported media to another instance.</Message> : null}
        <Muted>Native Studio runs the saved searches and their configured time ranges. The canvas uses bounded preview snapshots.</Muted>
        {busy ? <Muted role="status">Saving and checking the dashboard…</Muted> : null}
      </>}
    </Modal.Body><Modal.Footer>
      <Button disabled={busy} onClick={onClose}>{result ? 'Close' : 'Cancel'}</Button>
      {!result ? <Button appearance="primary" disabled={busy} onClick={() => { setBusy(true); setError(''); void saveCopy(definition, theme, app).then(saved => { setResult(saved); onSaved(saved); })
        .catch(failure => setError(failure instanceof Error ? failure.message : 'The dashboard could not be saved. Your draft is preserved.')).finally(() => setBusy(false)); }}>Save private copy</Button> : null}
    </Modal.Footer>
  </Modal>;
}
