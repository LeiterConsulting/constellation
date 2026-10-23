import type { DataDiscovery, DataScope } from './data';
import type { StudioDefinition } from './document';
import { validFocus, pagesOf, type PagePurpose } from './pages';

export interface PromptSuggestion { label: string; prompt: string; reason: string; kind: 'idea' | 'data' | 'comparison' | 'interaction' | 'layout' | 'refine'; }
export interface InstanceIdea extends PromptSuggestion { scope?: DataScope; }
export function instanceIdeas(discovery: DataDiscovery | null): InstanceIdea[] {
  if (!discovery) return [];
  const recent = [...discovery.activity].sort((a, b) => Number(a.index.startsWith('_')) - Number(b.index.startsWith('_')));
  const choices: typeof recent = [];
  for (const item of recent) if (!choices.some(choice => choice.index === item.index)) choices.push(item);
  for (const item of recent) if (!choices.some(choice => choice.index === item.index && choice.sourcetype === item.sourcetype)) choices.push(item);
  if (!choices.length) for (const item of discovery.indexes.filter(item => item.kind !== 'metric').slice(0, 3)) choices.push({ index: item.name, sourcetype: '', events: '' });
  return choices.slice(0, 3).map(item => ({ label: `${item.events ? 'Explore' : 'Inspect'} ${item.index}${item.sourcetype && choices.filter(choice => choice.index === item.index).length > 1 ? ` · ${item.sourcetype}` : ''}`, kind: 'data',
    reason: item.events ? `${item.sourcetype || 'This index'} has recent searchable activity. Inspect its fields and build from it.` : 'Visible in your Splunk catalog; check its fields and time coverage first.',
    prompt: `Build a useful dashboard using actual Splunk data in index=${item.index}${item.sourcetype ? `, sourcetype=${item.sourcetype}` : ''}. Use the verified fields to show event volume over time and useful breakdowns. Do not use illustrative data.`,
    scope: { index: item.index, sourcetype: item.sourcetype, earliest: '-24h', language: 'spl' },
  }));
}

export function promptContextKey(revision: number, definition: StudioDefinition, selected: string, activeTab?: string, data?: DataScope | null): string {
  const tabs = definition.layout.tabs as { items?: Array<{ layoutId: string }> } | undefined;
  const tab = tabs?.items?.find(item => item.layoutId === activeTab)?.layoutId || tabs?.items?.[0]?.layoutId || '';
  return JSON.stringify([revision, validFocus(definition, selected) ? selected : '', tab,
    data ? [data.index || '', data.sourcetype || '', data.query || '', data.language || 'spl', data.earliest] : null]);
}

export function contextualPrompts(definition: StudioDefinition, selected = '', attachments = 0, data?: DataScope | null, purposes: PagePurpose = {}): PromptSuggestion[] {
  if (attachments) return [{ label: 'Build from this reference', kind: 'layout', reason: 'Your attached reference is ready to guide the design.',
    prompt: 'Use the attached reference to shape this dashboard. Interpret its layout and intent, choose appropriate native Studio visualizations, and explain any approximation. Use the selected real data; ask for missing fields instead of fabricating values.' }];
  const page = selected.startsWith('page:') ? pagesOf(definition,purposes).find(page=>page.id===selected.slice(5)) : undefined;
  if (page) return [{label: page.items.length ? 'Refine this page' : 'Build this page',kind:'layout',reason:page.purpose || `Focus on the ${page.name} page.`,
    prompt:`${page.items.length?'Improve':'Build'} the selected page, ${page.name}, using its stated purpose and our conversation. Use verified Splunk fields and searches, preserve other pages, and create a clear visual hierarchy.`},
    {label:'Connect this page',kind:'interaction',reason:'Help readers move between the overview and relevant details.',
      prompt:'Add useful native navigation between the selected page and a related page using the existing dashboard context. Use a table row token when a verified field can filter the detail page; preserve working searches.'}];
  const input = (definition.inputs as Record<string,{type?:string;options?:{label?:string}}> | undefined)?.[selected];
  if (input?.type==='input.button') return [{label:'Refine this button',kind:'refine',reason:`Focus on ${input.options?.label || selected}.`,
    prompt:'Improve the selected button’s label and action using its purpose and the surrounding dashboard. Keep its behavior clear and preserve unrelated inputs and panels.'},
    {label:'Improve page navigation',kind:'interaction',reason:'Connect this button to the right page and investigation target.',
      prompt:'Refine the selected button’s native page navigation using our conversation and page purposes. Choose a useful destination and element focus, and preserve existing filters and return navigation.'}];
  if (input) return [{label:'Refine this input',kind:'refine',reason:`Focus on ${input.options?.label || selected}.`,
    prompt:'Improve the selected input using its purpose, verified fields and current token bindings. Make its label and choices clear, preserve working filters and keep it readable in both Splunk themes.'},
    {label:'Connect the filter',kind:'interaction',reason:'Make the input control the relevant panels.',prompt:'Connect the selected input to the relevant existing searches with safe native Studio tokens and a useful default. Validate the filtered searches, preserve other inputs and explain which panels it controls.'}];
  const chart = definition.visualizations[selected];
  if (chart) return [{ label: 'Refine this chart', kind: 'refine', reason: `Focus on ${chart.title || 'the selected chart'}.`,
    prompt: 'Help me improve the selected chart. Consider its purpose, existing fields and surrounding dashboard; propose the most useful visual or comparison change and preserve its data source.' },
  { label: 'Make it explorable', kind: 'interaction', reason: 'Connect this chart to the question behind a data point.',
    prompt: 'Add a useful native Studio interaction to the selected chart, using its existing fields and the dashboard context. Prefer a filter or a detail view that answers a relevant follow-up question. Preserve unrelated content.' }];
  const charts = Object.values(definition.visualizations);
  if (!charts.length && data) return [{ label: 'Build from the selected data', kind: 'data', reason: `Use ${data.index || 'your existing search'} and its verified fields.`,
    prompt: 'Build a focused dashboard from the selected Splunk data and our conversation. Use verified fields, actual read-only searches and a useful visual hierarchy. Do not add illustrative data.' }];
  if (!charts.length) return [{ label: 'Choose data for this question', kind: 'idea', reason: 'Start with the decision this dashboard should support.',
    prompt: 'Help me choose data from this Splunk instance for my dashboard question. Suggest a visible index or ask for my existing search, then inspect its actual fields before building.' }];
  const result: PromptSuggestion[] = [];
  if (Object.values(definition.dataSources || {}).some(source => source.type === 'ds.test')) result.push({ label: 'Connect real data', kind: 'data', reason: 'This design currently includes illustrative data.',
    prompt: 'Help me connect this design to real Splunk data. Identify the metrics and fields needed by the current charts. Ask for my existing searches or relevant field names before changing queries; preserve the layout while we connect them.' });
  if (charts.some(chart => chart.type === 'splunk.table' && !chart.eventHandlers)) result.push({ label: 'Add a useful drilldown', kind: 'interaction', reason: 'The table can become an entry point for investigation.',
    prompt: 'Make the existing table open a meaningful detail view using its actual fields and a native Studio token/tab drilldown. Preserve the rest of the dashboard and label synthetic examples.' });
  if (charts.some(chart => ['splunk.line', 'splunk.area', 'splunk.column'].includes(chart.type))) result.push({ label: 'Add a meaningful comparison', kind: 'comparison', reason: 'A baseline can help explain the trend already on the canvas.',
    prompt: 'Propose and add the most useful comparison for the current trend, using the dashboard goal, conversation and available fields. Reuse working searches and compatible verified fields. Ask for missing data before adding a comparison; do not fabricate a baseline.' });
  result.push({ label: 'Sharpen the visual story', kind: 'layout', reason: 'Make the key question and next action easier to see.',
    prompt: 'Refine this dashboard around its audience and main decision. Improve hierarchy, chart choices and spacing using the existing metrics and conversation. Preserve working searches and interactions.' });
  return result.slice(0, 3);
}
