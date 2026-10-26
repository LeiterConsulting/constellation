import type { DataProfile } from './data';
import type { StudioDefinition } from './document';
import type { PromptSuggestion } from './prompts';
import { isMeasurement, type ProfileField } from './fieldContext';
import { fieldTitle } from './datasetQuestions';

/** Optional suggestion evidence, not a query parser or an execution/validation guard. */
export function referencedFields(definition: StudioDefinition, charts: readonly string[], profile?: DataProfile | null): ProfileField[] {
  const seen = new Set<string>(), queries: string[] = [];
  const visit = (id: string) => {
    if (seen.has(id)) return;
    seen.add(id);
    const source = definition.dataSources?.[id];
    if (typeof source?.options?.query === 'string') queries.push(source.options.query);
    if (typeof source?.options?.extend === 'string') visit(source.options.extend);
  };
  charts.forEach(id => Object.values(definition.visualizations[id]?.dataSources || {}).forEach(visit));
  return (profile?.fields || []).filter(field => {
    const escaped = field.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return queries.some(query => new RegExp(`(?<![\\w.])${escaped}(?![\\w.])`, 'i').test(query));
  });
}

export function unitConfirmation(field: ProfileField): PromptSuggestion | null {
  const units: Record<string, string> = {'°F':'Fahrenheit','°C':'Celsius',ms:'milliseconds','µs':'microseconds',s:'seconds',dBm:'dBm','%':'percent',B:'bytes'};
  const unit = field.context?.unit;
  if (!isMeasurement(field) || field.context?.basis !== 'field_name' || !unit || !units[unit]) return null;
  return {label:`Confirm recorded units: ${fieldTitle(field.name)}`.slice(0,60),kind:'refine',
    prompt:`${JSON.stringify(field.name)} is recorded in ${units[unit]}.`,
    reason:`Name hint only: ${unit}. Send this confirmation only if it is the stored unit; edit it otherwise.`};
}
