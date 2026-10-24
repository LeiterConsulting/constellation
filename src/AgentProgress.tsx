import { useEffect, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import { progressLabel, type RunProgress } from './authoringRun';
import { Actions, ProgressStatus } from './styles';

export default function AgentProgress({ progress, onStop }: { progress: RunProgress | null; onStop: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => { const started = Date.now(); const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000); return () => clearInterval(timer); }, []);
  return <ProgressStatus aria-label="Agent progress"><Actions><span role="status">{progress ? progressLabel(progress) : 'Starting…'}</span><Button onClick={onStop}>Stop</Button></Actions>
    <small>{elapsed}s elapsed · Changes apply together after validation.</small>
    {elapsed >= 20 && progress?.stage === 'model' ? <small>The model is still responding. You can keep reading the dashboard or stop.</small> : null}
  </ProgressStatus>;
}
