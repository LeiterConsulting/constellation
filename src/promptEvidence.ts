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

/** Discard an optional repeated source-unit question only with scoped user evidence. */
export function redundantUnitQuestion(card: PromptSuggestion, profile?: DataProfile | null): boolean {
  const text = `${card.label} ${card.prompt}`;
  if (!/\b(?:confirm|verify|clarify|check|which|what|define)\b.{0,80}\b(?:units?|fahrenheit|celsius|dbm|milliseconds|seconds)\b/i.test(text)
      || /\b(?:convert\w*|conversion|display\w*|show|plot|format|label|axis|relabel\w*)\b/i.test(text)) return false;
  const fields = profile?.fields || [];
  const hasUnitMeaning = (field: ProfileField) => field.context?.role === 'measurement' || isMeasurement(field);
  const matches = (value: string) => fields.filter(field => {
    const escaped = field.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`(?<![\\w.])${escaped}(?!\\w|\\.\\w)`, 'i').test(value);
  });
  // The editable request's exact field wins over a generic display label that
  // happens to equal another inspected field (temperature vs temperature_f).
  const requested = matches(card.prompt);
  const named = requested.length ? requested : matches(card.label);
  const quantities = [
    [/\b(?:temp(?:eratures?)?|fahrenheit|celsius)\b/i, 'temperature'],
    [/\b(?:latency|duration|response time|milliseconds|seconds)\b/i, 'duration'],
    [/\b(?:rssi|wi-?fi|signal|dbm)\b/i, 'signal_strength'],
  ] as const;
  const mentioned = quantities.filter(([pattern]) => pattern.test(text)).map(([,quantity]) => quantity);
  const relevant = named.length ? named : mentioned.length ? fields.filter(field => mentioned.some(quantity => quantity === field.context?.quantity)) : fields.filter(hasUnitMeaning);
  return relevant.length > 0 && relevant.every(field => hasUnitMeaning(field) && field.context?.basis === 'user' && !!field.context.unit && !field.context.nameUnitConflict);
}
