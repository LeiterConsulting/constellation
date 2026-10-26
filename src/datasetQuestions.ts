import type { DataDiscovery, DataProfile, DataScope } from './data';
import type { InstanceIdea } from './prompts';

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
export function profileFields(profile?: DataProfile | null) {
  return profile?.fields.filter(field => field.present > 0 && !technical.test(field.name)) || [];
}

/** Questions grounded in observed schema, never inferred from an index's name or event values. */
export function datasetQuestions(profile?: DataProfile | null): InstanceIdea[] {
  if (!profile?.sampledRows) return [];
  const fields = profileFields(profile), numeric = fields.filter(field => field.numeric && !/(?:^|_)(?:id|pid|ppid|uid|gid|tid|port|code|timestamp|index|version|status|state|outcome|severity|level|enabled|valid|ok|wrapped)$/i.test(field.name));
  const temperature = numeric.find(field => /^(?:temperature|temp)[_ .-]?f$/i.test(field.name))
    || numeric.find(field => /^(?:temperature|temp)(?:[_ .-]?c)?$/i.test(field.name))
    || numeric.find(field => /(?:^|[_ .-])(?:temp(?:erature)?)(?:$|[_ .-])/i.test(field.name) && !/^(?:min|max|avg|mean)[_ .-]/i.test(field.name));
  const signal = numeric.find(field => /rssi|signal.*strength/i.test(field.name));
  const duration = numeric.find(field => /^(?:response[_. -]?(?:time|ms)|latency|duration)(?:[_. -]?(?:ms|seconds|s))?$/i.test(field.name))
    || numeric.find(field => /latency|duration|response[_. -]?(?:time|ms)|elapsed/i.test(field.name) && !/^counter_|count|censored|upper_bound|resolution|threshold|^avg_|^min_|^max_/i.test(field.name));
  const packetLoss = numeric.find(field => /^packet_loss(?:_pct|_percent)?$/i.test(field.name));
  const process = fields.find(field => /^process_name$/i.test(field.name)) || fields.find(field => /^command$/i.test(field.name));
  const processState = fields.find(field => /^process_state$/i.test(field.name));
  const outcome = fields.find(field => /(?:^|_)(?:status|state|outcome|result|severity|level|status_code|http_status)$/i.test(field.name));
  const entity = fields.find(field => !field.numeric && /^(?:device(?:_id|_name)?|service(?:_name)?|process_name|sensor(?:_id)?|name|entity|node|hostname)$/i.test(field.name))
    || fields.find(field => !field.numeric && field !== outcome)
    || profile.fields.find(field => field.name === 'host' && field.present > 0 && !field.numeric);
  const metric = temperature || duration || numeric[0];
  const dataset = profile.scope.index || 'your search';
  const scope = profile.scope;
  const prefix = 'Create a dashboard from the selected data. ';
  const guard = ' Use recorded units; ask me if units or limits are unclear.';
  const result: InstanceIdea[] = [];
  const add = (label: string, question: string, used: string[], kind: InstanceIdea['kind'] = 'data', benefit = 'See changes, current readings and their spread in one view.') => {
    const prompt = prefix + question + guard;
    if (prompt.length <= 1200) result.push({ label: label.slice(0, 60), kind, scope, profile, fields: used,
      reason: `${dataset} · ${benefit}${profile.completion?.state === 'partial' ? ' · partial field sample' : ''}`.slice(0, 200), prompt });
  };
  if (!profile.fields.some(field => field.name === '_time' && field.present > 0)) {
    if (metric) add(`Visualize ${fieldTitle(metric.name)}`,
      `Visualize the existing ${JSON.stringify(metric.name)} output${entity ? ` by ${JSON.stringify(entity.name)}` : ''}. Preserve the current search, output grain and aggregation. Do not invent a time axis or treat aggregate rows as raw events.`,
      [metric.name, ...(entity ? [entity.name] : [])], 'data', 'Make the existing search output readable while preserving its meaning.');
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
  if (!result.length && entity) add(`See what drives ${fieldTitle(entity.name)} activity`,
    `Show event arrivals over time and the contribution of each ${JSON.stringify(entity.name)}. Make it easy to investigate one ${JSON.stringify(entity.name)}, without treating event volume as a business outcome.`, [entity.name]);
  return result.slice(0, 3);
}
