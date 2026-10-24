import CollapsiblePanel from '@splunk/react-ui/CollapsiblePanel';
import Message from '@splunk/react-ui/Message';
import type { ModelReadinessReport } from './api';
import { Muted } from './styles';

export default function ModelReadiness({ report }: { report: ModelReadinessReport }) {
  return <>
    <Message type="warning">{report.warnings[0]}</Message>
    <CollapsiblePanel title="Model limits and test details" appearance="subtle">
      <Muted>{report.scope}</Muted>
      <dl>{report.limits.map(limit => <div key={limit.label}><dt><strong>{limit.label}</strong></dt><dd>{limit.value}</dd></div>)}</dl>
      {report.warnings.slice(1).map(warning => <Muted key={warning}>{warning}</Muted>)}
      {report.tested ? Object.entries(report.usage).length ? <Muted>Test usage: {Object.entries(report.usage).map(([key, count]) => `${count?.toLocaleString()} ${key.replaceAll('_', ' ')}`).join(' · ')}. Reasoning is included in output usage when reported.</Muted> : <Muted>The provider did not report token usage for this test.</Muted> : null}
    </CollapsiblePanel>
  </>;
}
