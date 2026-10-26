import type { DataDiscovery, DataProfile, DataScope } from './data';
import type { InstanceIdea } from './prompts';
import { hasMissing, isMeasurement } from './fieldContext';

export function starterScopes(discovery: DataDiscovery, preferred?: DataScope | null): DataScope[] {
  const events = new Set(discovery.indexes.filter(item => item.kind !== 'metric').map(item => item.name));
  const recent = discovery.activity.filter(item => events.has(item.index))
    .sort((a, b) => Number(a.index.startsWith('_')) - Number(b.index.startsWith('_')));
  const chosen: DataScope[] = [];
  if (preferred && (preferred.query || (preferred.index && events.has(preferred.index)))) chosen.push(preferred);
  for (const item of recent) {
    if (!chosen.some(scope => scope.index === item.index)) chosen.push({ index: item.index, sourcetype: item.sourcetype, earliest: '-24h', language: 'spl' });
    if (chosen.length === 3) break;
  }
  return chosen;
}

const technical = /^(?:_.*|date_.*|timeendpos|timestartpos|punct|linecount|index|source|sourcetype|splunk_server(?:_group)?|host)$/i;
const words = (name: string) => name.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_.:-]+/g, ' ').trim();
export const fieldTitle = (name: string) => words(name).slice(0, 48);
export function profileFields(profile?: DataProfile | null, includeEmpty = false) {
  return profile?.fields.filter(field => (includeEmpty || field.present > 0) && !technical.test(field.name)) || [];
}

/** Questions grounded in observed schema, never inferred from an index's name or event values. */
export function datasetQuestions(profile?: DataProfile | null): InstanceIdea[] {
  if (!profile?.sampledRows) return [];
  const fields = profileFields(profile), numeric = fields.filter(field => isMeasurement(field) && !/(?:^|_)(?:id|pid|ppid|uid|gid|tid|port|code|timestamp|index|version|status|state|outcome|severity|level|enabled|valid|ok|wrapped)$/i.test(field.name));
  const temperature = numeric.find(field => field.context?.quantity === 'temperature' && field.context.basis === 'user')
    || numeric.find(field => /^(?:temperature|temp)[_ .-]?f$/i.test(field.name))
    || numeric.find(field => /^(?:temperature|temp)(?:[_ .-]?c)?$/i.test(field.name))
    || numeric.find(field => /(?:^|[_ .-])(?:temp(?:erature)?)(?:$|[_ .-])/i.test(field.name) && !/^(?:min|max|avg|mean)[_ .-]/i.test(field.name));
  const signal = numeric.find(field => field.context?.quantity === 'signal_strength' && field.context.basis === 'user') || numeric.find(field => /rssi|signal.*strength/i.test(field.name));
  const duration = numeric.find(field => field.context?.quantity === 'duration' && field.context.basis === 'user')
    || numeric.find(field => field.context?.quantity === 'duration' && field.context.unit && /^(?:response[_. -]?time|latency)(?:[_. -]?(?:ms|us|seconds|s))?$/i.test(field.name))
    || numeric.find(field => field.context?.quantity === 'duration' && field.context.unit)
    || numeric.find(field => /^(?:response[_. -]?(?:time|ms)|latency|duration)(?:[_. -]?(?:ms|seconds|s))?$/i.test(field.name))
    || numeric.find(field => /latency|duration|response[_. -]?(?:time|ms)|elapsed/i.test(field.name) && !/^counter_|count|censored|upper_bound|resolution|threshold|^avg_|^min_|^max_/i.test(field.name));
  const packetLoss = numeric.find(field => /^packet_loss(?:_pct|_percent)?$/i.test(field.name));
  const process = fields.find(field => /^process_name$/i.test(field.name)) || fields.find(field => /^command$/i.test(field.name));
  const processState = fields.find(field => /^process_state$/i.test(field.name));
  const outcome = fields.find(field => field.context?.role !== 'counter' && !/^counter_/i.test(field.name) && /(?:^|_)(?:status|state|outcome|result|severity|level|status_code|http_status)$/i.test(field.name));
  const entity = fields.find(field => !field.numeric && /^(?:device(?:_id|_name)?|service(?:_name)?|process_name|sensor(?:_id)?|name|entity|node|hostname)$/i.test(field.name))
    || fields.find(field => !field.numeric && field !== outcome && !['counter','measurement','timestamp'].includes(field.context?.role || '') && !/^counter_/i.test(field.name))
    || profile.fields.find(field => field.name === 'host' && field.present > 0 && !field.numeric);
  const metric = temperature || duration || numeric.find(field => !field.context || field.context.role === 'measurement');
  const unconfirmed = numeric.find(field => field.context?.role === 'unknown');
  const dataset = profile.scope.index || 'your search';
  const scope = profile.scope;
  const prefix = 'Create a dashboard from the selected data. ';
  const guard = ' Use recorded units; ask me if units or limits are unclear.';
  const result: InstanceIdea[] = [];
  const add = (label: string, question: string, used: string[], kind: InstanceIdea['kind'] = 'data', benefit = 'See changes, current readings and their spread in one view.') => {
    const usedFields = fields.filter(field => used.includes(field.name));
    const missing = usedFields.filter(hasMissing);
    const unitContext = usedFields.filter(field => field.context?.quantity && field.context.role === 'measurement').map(field => field.context?.unit
      ? `${JSON.stringify(field.name)} uses ${field.context.unit} according to ${field.context.basis === 'user' ? 'my definition' : 'its name (a hint, not independent verification)'}.`
      : `Confirm the recorded units of ${JSON.stringify(field.name)} before applying thresholds or conversions.`).join(' ');
    const coverage = missing.length ? ` Include independent valid-reading counts for ${missing.map(field => JSON.stringify(field.name)).join(', ')} and source-row counts. Keep missing or nonnumeric measurements null; do not fill with zero or drop independent readings.` : '';
    const prompt = prefix + question + (unitContext ? ' ' + unitContext : '') + coverage + guard;
    if (prompt.length <= 1200) result.push({ label: label.slice(0, 60), kind, scope, profile, fields: used,
      reason: `${dataset} · ${benefit}${profile.completion?.state === 'partial' ? ' · partial field sample' : ''}`.slice(0, 200), prompt });
  };
  if (!profile.fields.some(field => field.name === '_time' && field.present > 0)) {
    const outputMetric = metric || fields.find(field=>field.numeric && !['identifier','category','timestamp'].includes(field.context?.role || ''));
    if (outputMetric) add(`Visualize ${fieldTitle(outputMetric.name)}`,
      `Visualize the existing ${JSON.stringify(outputMetric.name)} output${entity ? ` by ${JSON.stringify(entity.name)}` : ''}. Preserve the current search, output grain and aggregation. Do not invent a time axis or treat aggregate rows as raw events.`,
      [outputMetric.name, ...(entity ? [entity.name] : [])], 'data', 'Make the existing search output readable while preserving its meaning.');
    return result;
  }
  if (temperature) add(signal ? 'Track temperature and connectivity' : 'Track temperature over time',
    `Show ${JSON.stringify(temperature.name)} over time, its latest value and typical range.${signal ? ` Compare ${JSON.stringify(signal.name)} over the same window without discarding independent readings.` : ''}${entity ? ` Make it possible to focus on ${JSON.stringify(entity.name)}.` : ''}`,
    [temperature.name, ...(signal ? [signal.name] : []), ...(entity ? [entity.name] : [])], 'data', signal ? 'Follow temperature changes alongside connectivity.' : 'Follow current readings, changes and their typical range.');
  else if (packetLoss) add('Track packet loss and device states',
    `Show ${JSON.stringify(packetLoss.name)} over time${entity ? ` by ${JSON.stringify(entity.name)}` : ''}.${outcome ? ` Show the recorded ${JSON.stringify(outcome.name)} values alongside it without assuming what each state means.` : ''} Include observation counts and a focused device view.`,
    [packetLoss.name, ...(outcome ? [outcome.name] : []), ...(entity ? [entity.name] : [])], 'data', 'Show loss readings alongside recorded device states.');
  else if (process && processState) add('Monitor process states',
    `Show recorded ${JSON.stringify(processState.name)} over time for ${JSON.stringify(process.name)}, with observation counts and last-seen time. Make it easy to investigate one process. Treat process IDs as identifiers, not performance measurements.`,
    [process.name,processState.name], 'data', 'Review process observations and investigate an individual process.');
  else if (duration) add(outcome ? 'Investigate response time and outcomes' : 'Investigate slow responses',
    `Show the distribution and time trend of ${JSON.stringify(duration.name)}, including median and upper-percentile measurements.${outcome ? ` Add a breakdown by ${JSON.stringify(outcome.name)} without assuming which values mean failure.` : ''}${entity ? ` Compare by ${JSON.stringify(entity.name)}.` : ''}`,
    [duration.name, ...(outcome ? [outcome.name] : []), ...(entity ? [entity.name] : [])], 'data', 'See typical response times, slow tails and the outcome mix.');
  else if (metric) add(`Understand ${fieldTitle(metric.name)}`,
    `Show the time trend, latest value and distribution of ${JSON.stringify(metric.name)}.${entity ? ` Compare it by ${JSON.stringify(entity.name)} where the inspected search retains that field.` : ''}`,
    [metric.name, ...(entity ? [entity.name] : [])]);
  if (entity && metric) add(`Compare ${fieldTitle(entity.name)} performance`,
    `Compare ${JSON.stringify(metric.name)} across ${JSON.stringify(entity.name)}, showing both typical values and measurement counts. Add a focused view for investigating one ${JSON.stringify(entity.name)}; preserve the same population and time window.`,
    [entity.name, metric.name], 'comparison', 'Compare typical values and counts before investigating one entity.');
  if (outcome) add('Understand outcomes over time',
    `Show the mix of ${JSON.stringify(outcome.name)} values over time${entity ? ` and by ${JSON.stringify(entity.name)}` : ''}. Include event counts so small populations remain visible. Do not assume failure/success meanings without verified definitions.`,
    [outcome.name, ...(entity ? [entity.name] : [])], 'data', 'See how the mix of recorded outcomes changes.');
  if (!result.length && unconfirmed) add(`Clarify ${fieldTitle(unconfirmed.name)}`,
    `First ask what ${JSON.stringify(unconfirmed.name)} represents and which units are recorded before building calculations. Establish whether it is a measurement, identifier, state or counter; do not average an undefined numeric field.`, [unconfirmed.name], 'refine', 'Its numeric shape does not establish meaning or units.');
  if (!result.length && entity) add(`See what drives ${fieldTitle(entity.name)} activity`,
    `Show event arrivals over time and the contribution of each ${JSON.stringify(entity.name)}. Make it easy to investigate one ${JSON.stringify(entity.name)}, without treating event volume as a business outcome.`, [entity.name]);
  return result.slice(0, 3);
}
