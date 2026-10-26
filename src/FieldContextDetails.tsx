import Table from '@splunk/react-ui/Table';
import type { DataProfile } from './data';
import { profileFields } from './datasetQuestions';
import { fieldMeaning, sampleCoverage, unitHint } from './fieldContext';
import { Muted } from './styles';
export default function FieldContext({ profile }: { profile: DataProfile }) {
  const priority = (field: DataProfile['fields'][number]) => field.context?.basis === 'user' || field.context?.meaningBasis === 'user' ? 0 : field.context?.role === 'measurement' ? 1 : field.context?.role === 'identifier' ? 2 : 3;
  const fields = [...profileFields(profile, true)].sort((a,b)=>priority(a)-priority(b));
  const remaining = profile.fields.filter(field=>!fields.some(shown=>shown.name===field.name));
  return <details><summary>Field context</summary>
    <Muted>Name hints need confirmation. Describe field meanings and recorded units in your question. Missing is separate from zero; counts below describe only the inspected rows.</Muted>
    <Table stripeRows><Table.Head><Table.HeadCell>Field</Table.HeadCell><Table.HeadCell>Meaning / units</Table.HeadCell><Table.HeadCell>Sample</Table.HeadCell></Table.Head>
      <Table.Body>{fields.map(field => <Table.Row key={field.name}><Table.Cell>{field.name}</Table.Cell>
        <Table.Cell>{fieldMeaning(field)}{field.context?.quantity || field.context?.unit ? ` · ${unitHint(field)}` : ''}</Table.Cell>
        <Table.Cell>{sampleCoverage(field, profile.sampledRows)}</Table.Cell></Table.Row>)}</Table.Body></Table>
    {remaining.length ? <Muted>Other inspected fields: {remaining.map(field=>field.name).join(', ')}.</Muted> : null}
  </details>;
}
