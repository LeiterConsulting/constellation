import type { DataProfile, DataScope } from './data';
import type { DashboardBrief, ChatMessage } from './drafts';
import type { PreviewRows } from './agent';
import type { StudioDefinition } from './document';
import { validFocus, pagesOf, type PagePurpose } from './pages';
import { elementLabel } from './elementLabels';
import { fieldTitle, profileFields } from './datasetQuestions';
import { hasMissing, isMeasurement } from './fieldContext';
import { referencedFields, unitConfirmation } from './promptEvidence';

export interface PromptSuggestion { label: string; prompt: string; reason: string; kind: 'idea' | 'data' | 'comparison' | 'interaction' | 'layout' | 'refine'; focus?: string; }
export const suggestionFocus = (suggestion: PromptSuggestion, definition: StudioDefinition) => typeof suggestion.focus==='string' && validFocus(definition,suggestion.focus) ? suggestion.focus : null;
export interface InstanceIdea extends PromptSuggestion { scope?: DataScope; profile?: DataProfile; fields?: string[]; }
export interface PromptContext {
  brief?: DashboardBrief; messages?: Pick<ChatMessage, 'user' | 'text'>[]; profile?: DataProfile | null;
  results?: Record<string, PreviewRows>; activeTab?: string;
}
const recentRequests = (context: PromptContext) => (context.messages || []).filter(message => message.user).slice(-3).map(message => message.text);
const intentText = (context: PromptContext) => [context.brief?.purpose, context.brief?.requirements, ...recentRequests(context)].filter(Boolean).join('\n');
export function suggestionsDeclined(context: PromptContext) {
  let declined = false;
  for (const text of [context.brief?.purpose || '', context.brief?.requirements || '', ...(context.messages || []).filter(message => message.user).map(message => message.text)]) {
    if (/\b(?:no (?:more |follow[- ]?up )?suggestions|stop suggesting|(?:do not|don['’]t) (?:offer |show |give me )?suggest)/i.test(text)) declined = true;
    else if (/\b(?:show|offer|resume|give me)\b.{0,25}\bsuggestions\b|\bsuggest\b.{0,25}\bnext\b/i.test(text)) declined = false;
  }
  return declined;
}
export function promptContextKey(revision: number, definition: StudioDefinition, selected: string, activeTab?: string, data?: DataScope | null, context: PromptContext = {}): string {
  const tabs = definition.layout.tabs as { items?: Array<{ layoutId: string }> } | undefined;
  const tab = tabs?.items?.find(item => item.layoutId === activeTab)?.layoutId || tabs?.items?.[0]?.layoutId || '';
  return JSON.stringify([revision, validFocus(definition, selected) ? selected : '', tab,
    data ? [data.index || '', data.sourcetype || '', data.query || '', data.language || 'spl', data.earliest] : null,
    context.brief?.purpose || '', context.brief?.requirements || '', recentRequests(context)]);
}

export function contextualPrompts(definition: StudioDefinition, selected = '', attachments = 0, data?: DataScope | null, purposes: PagePurpose = {}, context: PromptContext = {}): PromptSuggestion[] {
  if (suggestionsDeclined(context)) return [];
  if (attachments) return [{ label: 'Build from this reference', kind: 'layout', reason: 'Your attached reference is ready to guide the design.',
    prompt: 'Use the attached reference to shape this dashboard. Interpret its layout and intent, choose appropriate native Studio visualizations, and explain any approximation. Use the selected real data; ask for missing fields instead of fabricating values.' }];
  const question = [...(context.messages || [])].reverse().find(message => !message.user)?.text.trim() || '';
  if (question.endsWith('?')) {
    const field = context.profile?.fields.find(field => question.includes(field.name) && /recorded|stored|measured/i.test(question));
    const confirmation = field && unitConfirmation(field);
    if (confirmation) return [confirmation];
    if (/fahrenheit/i.test(question) && /celsius/i.test(question)) return ['Fahrenheit','Celsius'].map(unit => ({label:`Use ${unit}`,kind:'refine',reason:'Answer the temperature-units question so building can continue.',
      prompt:`Use ${unit} for temperatures on this dashboard. Continue the original request and keep its other requirements.`}));
    return [];
  }
  if (context.profile && !context.profile.sampledRows) return [];
  const page = selected.startsWith('page:') ? pagesOf(definition,purposes).find(page=>page.id===selected.slice(5)) : undefined;
  if (page) return [{label: page.items.length ? 'Refine this page' : 'Build this page',kind:'layout',reason:page.purpose || `Focus on the ${page.name} page.`,
    prompt:`${page.items.length?'Improve':'Build'} the selected page, ${page.name}, using its stated purpose and our conversation. Use verified Splunk fields and searches, preserve other pages, and create a clear visual hierarchy.`},
    {label:'Connect this page',kind:'interaction',reason:'Help readers move between the overview and relevant details.',
      prompt:'Add useful native navigation between the selected page and a related page using the existing dashboard context. Use a table row token when a verified field can filter the detail page; preserve working searches.'}];
  const input = (definition.inputs as Record<string,{type?:string;options?:{label?:string}}> | undefined)?.[selected];
  if (input?.type==='input.button') return [{label:'Refine this button',kind:'refine',reason:`Focus on ${elementLabel(definition,selected)}.`,
    prompt:'Improve the selected button’s label and action using its purpose and the surrounding dashboard. Keep its behavior clear and preserve unrelated inputs and panels.'},
    {label:'Improve page navigation',kind:'interaction',reason:'Connect this button to the right page and investigation target.',
      prompt:'Refine the selected button’s native page navigation using our conversation and page purposes. Choose a useful destination and element focus, and preserve existing filters and return navigation.'}];
  if (input) return [{label:'Refine this input',kind:'refine',reason:`Focus on ${elementLabel(definition,selected)}.`,
    prompt:'Improve the selected input using its purpose, verified fields and current token bindings. Make its label and choices clear, preserve working filters and keep it readable in both Splunk themes.'},
    {label:'Connect the filter',kind:'interaction',reason:'Make the input control the relevant panels.',prompt:'Connect the selected input to the relevant existing searches with safe native Studio tokens and a useful default. Validate the filtered searches, preserve other inputs and explain which panels it controls.'}];
  const chart = definition.visualizations[selected];
  const pageItems = pagesOf(definition).find(page => page.id === context.activeTab)?.items;
  const entries = chart ? [[selected, chart] as const] : Object.entries(definition.visualizations).filter(([id]) => !pageItems || pageItems.includes(id));
  const charts = entries.map(([, chart]) => chart);
  if (!charts.length && data) return [{ label: 'Build from the selected data', kind: 'data', reason: `Use ${data.index || 'your existing search'} and its verified fields.`,
    prompt: 'Build a focused dashboard from the selected Splunk data and our conversation. Use verified fields, actual read-only searches and a useful visual hierarchy. Do not add illustrative data.' }];
  if (!charts.length) return [{ label: 'Choose data for this question', kind: 'idea', reason: 'Start with the decision this dashboard should support.',
    prompt: 'Help me choose data from this Splunk instance for my dashboard question. Suggest a visible index or ask for my existing search, then inspect its actual fields before building.' }];
  const result: PromptSuggestion[] = [], fields = profileFields(context.profile ? {...context.profile,fields:referencedFields(definition,entries.map(([id])=>id),context.profile)} : null);
  const entity = fields.find(field => !field.numeric && /device|service|sensor|host|name|entity/i.test(field.name));
  const noTables = /\b(?:no|without)\s+(?:any\s+)?tables?\b|\b(?:do not|don['’]t)\s+(?:add|include|use)\s+(?:any\s+)?tables?\b/i.test(intentText(context));
  const preserve = ' Keep the current data, time range and standing requirements; preserve the rest of the dashboard.';
  if (charts.some(item => definition.dataSources?.[String(item.dataSources?.primary)]?.type === 'ds.test')) result.push({ label: 'Connect real data', kind: 'data', reason: chart ? `${elementLabel(definition,selected)} currently uses illustrative data.` : 'This design currently includes illustrative data.',
    prompt: 'Help me connect this design to real Splunk data. Identify the metrics and fields needed by the current charts. Ask for my existing searches or relevant field names before changing queries; preserve the layout while we connect them.' });
  const ambiguous = fields.find(field => isMeasurement(field) && field.context?.quantity && !field.context.unit);
  const confirmation = fields.map(unitConfirmation).find(card => card !== null);
  if (confirmation) result.push(confirmation);
  if (ambiguous) result.push({label:`Confirm ${fieldTitle(ambiguous.name)} units`.slice(0,60),kind:'refine',reason:'Recorded units have not been defined; comparisons and limits need that context.',
    prompt:`Help me confirm the recorded units and meaning of ${JSON.stringify(ambiguous.name)} before adding thresholds or conversions. Ask one short question, keep the current measurements unchanged, and retain my answer in the dashboard requirements.`});
  const lastRequest = recentRequests(context).at(-1) || '';
  if (chart && /\b(?:colou?rs?|palette|theme|contrast)\b/i.test(lastRequest)) result.unshift({label:'Give this tile a contrasting background',kind:'refine',reason:`Make ${elementLabel(definition, selected)} readable without changing the whole dashboard.`,
    prompt:'Change only the selected tile’s native background and text/series colors to create readable contrast. Keep labels, axes, legends and values readable. Keep the dashboard theme and every other tile unchanged.'});
  const table = entries.find(([, item]) => item.type === 'splunk.table' && !(item.eventHandlers as {type?:string}[] | undefined)?.some(handler => /switchToTab|setToken/.test(handler.type || '')));
  if (table && !noTables) result.push({ label: 'Open a detail page from a row', kind: 'interaction', focus:table[0], reason: `${elementLabel(definition, table[0])} can lead directly to an investigation.`,
    prompt: `Make ${JSON.stringify(elementLabel(definition, table[0]))} open a focused detail page from a table row. Use an actual verified row field for a native token filter, apply that filter to the detail searches, and add return navigation.${preserve}` });
  const trend = entries.find(([, item]) => ['splunk.line', 'splunk.area'].includes(item.type) &&
    ['ds.search','ds.spl2','ds.chain'].includes(definition.dataSources?.[String(item.dataSources?.primary)]?.type || '') &&
    (String(item.options?.x).includes('_time') || context.results?.[String(item.dataSources?.primary)]?.fields.some(field => field.name === '_time')));
  if (trend && !/\b(?:streamstats|rolling|moving average|baseline)\b/i.test(JSON.stringify(definition.dataSources?.[String(trend[1].dataSources?.primary)] || {}))) result.push({ label: 'Add a rolling baseline', kind: 'comparison', focus:trend[0], reason: `Give ${elementLabel(definition, trend[0])} a reference for judging change.`,
    prompt: `Add a rolling average to ${JSON.stringify(elementLabel(definition, trend[0]))}. Keep the original series and explain the averaging window.${preserve}` });
  const filters = Object.values((definition.inputs || {}) as Record<string,{type?:string}>).some(item => item.type && !['input.button','input.timerange'].includes(item.type));
  if (entity && !filters) result.push({label:`Focus on one ${fieldTitle(entity.name)}`.slice(0,60),kind:'interaction',reason:`Use ${entity.name} to narrow the view without losing the overview.`,
    prompt:`Add a clearly labelled native ${JSON.stringify(entity.name)} filter with an all-values default. Connect it to the relevant searches and preserve working drilldowns.${preserve}`});
  if (fields.some(field => isMeasurement(field) && hasMissing(field))) result.unshift({label:'Show how many readings support each metric',kind:'data',reason:'The inspected sample has missing measurements. Counts distinguish absent readings from zero.',
    prompt:`Add valid measurement counts alongside the dashboard’s existing numeric summaries. Count each measurement independently, retain event counts separately, and keep missing or excluded measurements null.${preserve}`});
  if (chart?.type === 'splunk.singlevalue' && context.profile?.fields.some(field => field.name === '_time')) result.push({label:'Show how this metric changed',kind:'comparison',reason:`Put ${elementLabel(definition,selected)} in its time context.`,
    prompt:`Add a companion time trend for the selected metric using the same verified measurement and population.${preserve}`});
  if (chart && ['splunk.bar','splunk.column','splunk.pie'].includes(chart.type) && ['ds.search','ds.spl2','ds.chain'].includes(definition.dataSources?.[String(chart.dataSources?.primary)]?.type || '')) result.push({label:'Show each category’s share',kind:'comparison',reason:`Give the values in ${elementLabel(definition,selected)} context within their total.`,
    prompt:`Add a clearly labelled share-of-total view for the selected chart’s existing numeric measure and categories. Reuse the same verified search output and population. Handle an empty or zero total explicitly rather than inventing percentages.${preserve}`});
  return result.slice(0, 3);
}

/** Keep optional model cards useful, supplement empty replies, and avoid replaying completed requests. */
export function nextSuggestions(proposed: PromptSuggestion[], fallback: PromptSuggestion[], context: PromptContext): PromptSuggestion[] {
  if (suggestionsDeclined(context)) return [];
  const retry = proposed.find(item => /^retry\b/i.test(item.label));
  if (retry) return [retry];
  const seen = new Set<string>(), completed = new Set(recentRequests(context).map(text => text.trim().toLocaleLowerCase()));
  const generic = /^(?:refine this (?:chart|dashboard)|make it (?:better|explorable)|sharpen the visual story|add a (?:useful drilldown|meaningful comparison)|improve (?:the|this) dashboard)$/i;
  const noTables = /\b(?:no|without)\s+(?:any\s+)?tables?\b|\b(?:do not|don['’]t)\s+(?:add|include|use)\s+(?:any\s+)?tables?\b/i.test(intentText(context));
  const confirmations = fallback.filter(item => item.label.startsWith('Confirm recorded units:'));
  const candidates = confirmations.length ? [...confirmations,...proposed.filter(item=>!/\b(?:confirm|verify|clarify|check)\b.{0,40}\bunits?\b/i.test(item.label)),...fallback.filter(item=>!confirmations.includes(item))] : [...proposed,...fallback];
  return candidates.filter(item => {
    const key = item.prompt.trim().toLocaleLowerCase(), label = item.label.trim().toLocaleLowerCase();
    if (!key || item.prompt.length > 1200 || generic.test(label) || seen.has(key) || seen.has('label:' + label) || (completed.has(key) && !/^retry\b/i.test(label))) return false;
    if (noTables && /\btable\b/i.test(item.label) && !/\b(?:remove|replace|delete)\b/i.test(item.label)) return false;
    seen.add(key); seen.add('label:' + label); return true;
  }).slice(0, 3).map(item => ({...item,label:item.label.slice(0,60),reason:item.reason.slice(0,200)}));
}
