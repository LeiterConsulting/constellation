import { useEffect, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import ComboBox from '@splunk/react-ui/ComboBox';
import Select from '@splunk/react-ui/Select';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import { providerRequest, secureSettingsOrigin, type ProviderSettings, type ProviderName } from './api';
import { Actions, Muted } from './styles';

interface Props { onClose: () => void; onSaved: (settings: ProviderSettings) => void; returnFocus: React.RefObject<HTMLElement | null>; }
export default function Settings({ onClose, onSaved, returnFocus }: Props) {
  const [apiKey, setApiKey] = useState('');
  const [provider, setProvider] = useState<ProviderName>('openai');
  const [model, setModel] = useState('');
  const [endpoint, setEndpoint] = useState('http://localhost:11434');
  const [connection, setConnection] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [saved, setSaved] = useState<ProviderSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true), [loaded, setLoaded] = useState(false), [reload, setReload] = useState(0);
  const [status, setStatus] = useState('Loading connection…');
  const [error, setError] = useState(false);
  const secure = secureSettingsOrigin();
  const canStoreKey = saved?.keyStorage?.canWrite !== false;
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(false);
    void providerRequest<ProviderSettings>('settings', undefined, controller.signal).then(settings => {
      setSaved(settings); setProvider(settings.provider); setModel(settings.model);
      setHasKey(settings.connections?.openai?.keyConfigured || settings.keyConfigured);
      setEndpoint(settings.connections?.ollama?.base_url || 'http://localhost:11434');
      setConnection(settings.connections?.aitk?.connection || '');
      setLoaded(true);
      setStatus(settings.configured || settings.keyConfigured ? 'Your connection is saved. Choose a model or test it.' : 'Choose a provider to get started.');
    }).catch(reason => { if (!controller.signal.aborted) { setError(true); setStatus(reason instanceof Error ? reason.message : 'Connection settings could not be loaded.'); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); };
  }, [reload]);
  const chooseProvider = (value: ProviderName) => {
    setProvider(value); setApiKey(''); setModels([]); setError(false);
    setModel(saved?.connections?.[value]?.model || '');
    setStatus('Save to use this connection. Your other provider settings are retained.');
  };
  const run = async (operation: () => Promise<void>) => {
    setBusy(true); setError(false);
    try { await operation(); } catch (reason) { setError(true); setStatus(reason instanceof Error ? reason.message : 'The connection action failed.'); }
    finally { setBusy(false); }
  };
  const save = async () => {
    const settings = await providerRequest<ProviderSettings>('settings', { provider, apiKey, model, baseUrl: endpoint, connection });
    setApiKey(''); setHasKey(settings.connections?.openai?.keyConfigured || false); setSaved(settings); onSaved(settings);
    setStatus('Connection saved. Test it when ready.');
  };
  const valid = loaded && !loading && (provider === 'openai' ? canStoreKey && !!(apiKey || hasKey) && (secure || !apiKey) : provider === 'ollama' ? !!endpoint.trim() : !!connection.trim());
  return <Modal open onRequestClose={() => { setApiKey(''); onClose(); }} returnFocus={returnFocus} style={{ width: 'min(620px, calc(100vw - 32px))' }}>
    <Modal.Header title="AI connection"/>
    <Modal.Body id="constellation-settings">
      <ControlGroup label="Provider"><Select value={provider} disabled={busy || loading || !loaded} onChange={(_event, { value }) => chooseProvider(value as ProviderName)}>
        <Select.Option label="OpenAI" value="openai"/><Select.Option label="Ollama" value="ollama"/><Select.Option label="Splunk AITK" value="aitk"/>
      </Select></ControlGroup>
      {provider === 'openai' ? <>
        <Muted>https://api.openai.com/v1</Muted>
        {!secure ? <Message type="warning">Open through HTTPS to enter a key.</Message> : null}
        {!canStoreKey ? <Message type="info">OpenAI setup requires permission to manage encrypted credentials in Splunk. Ask your administrator to review this access, or choose Ollama or an authorized AITK connection. Constellation does not grant roles.</Message> : null}
        <ControlGroup label={hasKey ? 'Replace API key (optional)' : 'API key'} help="Stored encrypted in Splunk with owner-restricted permissions. The saved key is never returned to this form.">
          <Text type="password" autoComplete="new-password" value={apiKey} onChange={(_event, { value }) => setApiKey(value)} disabled={!secure || !canStoreKey || busy || loading || !loaded} canClear/>
        </ControlGroup>
      </> : provider === 'ollama' ? <ControlGroup label="Ollama server" help="An origin reachable from the Splunk server, such as http://server:11434. Localhost means the Splunk host. HTTPS certificates are verified.">
        <Text value={endpoint} onChange={(_event, { value }) => setEndpoint(value)} disabled={busy || loading || !loaded}/>
      </ControlGroup> : <ControlGroup label="AITK connection name" help="Use an existing LLM connection from AI Toolkit → Connections. AITK keeps its credentials and configured model; your Splunk permissions apply.">
        <Text value={connection} onChange={(_event, { value }) => setConnection(value)} disabled={busy || loading || !loaded}/>
      </ControlGroup>}
      {provider !== 'aitk' ? <ControlGroup label="Model" help="Load installed or available models, or enter an exact model ID. The model test verifies JSON edits.">
        <ComboBox value={model} onChange={(_event, { value }) => setModel(value)} disabled={busy || loading || !loaded} noOptionsMessage="Enter a model ID, or load available models.">
          {models.map(id => <ComboBox.Option key={id} value={id}/>)}
        </ComboBox>
      </ControlGroup> : null}
      <Actions>
        <Button appearance="primary" disabled={busy || !valid} onClick={() => void run(save)}>Save connection</Button>
        {provider !== 'aitk' ? <Button disabled={busy || !valid} onClick={() => void run(async () => {
          await save(); const result = await providerRequest<{ models: string[] }>('models', {}); setModels(result.models); setStatus(`Found ${result.models.length} models. Choose one and save.`);
        })}>Load models</Button> : null}
        <Button disabled={busy || !valid || (provider !== 'aitk' && !model)} onClick={() => void run(async () => {
          await save(); const result = await providerRequest<{ message: string }>('test', {}); setStatus(result.message);
        })}>Test model</Button>
      </Actions>
      {!loaded && !loading ? <Button onClick={() => setReload(value => value + 1)}>Retry loading settings</Button> : null}
      <Muted>Testing sends a small request and may incur provider charges. Chat sends dashboard configuration, recent conversation, index metadata, and supported attachments you send. Search result rows stay in Splunk and your browser.</Muted>
      {provider === 'aitk' ? <Muted>Text only on this route. Prompts use synthetic AITK search jobs and follow Splunk’s search retention. Adjust model and output limits in AI Toolkit.</Muted> : provider === 'ollama' ? <Muted>Images require the model’s advertised vision capability. PDFs are blocked on this route.</Muted> : null}
      <Message type={error ? 'error' : 'info'}><span role="status">{loading ? 'Loading connection…' : busy ? 'Working…' : status}</span></Message>
    </Modal.Body>
    <Modal.Footer><Button onClick={() => { setApiKey(''); onClose(); }} disabled={busy}>Close</Button></Modal.Footer>
  </Modal>;
}
