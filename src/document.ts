import starter from './starter.json';
import { previewDependencyQuery } from './previewSources';
import { previewImage } from './mediaReferences';
import { initializePreviewDefaults, type InputDefaults } from './previewDefaults';

export type JsonObject = Record<string, unknown>;
export interface Visualization extends JsonObject { type: string; title?: string; options?: JsonObject; dataSources?: Record<string, string>; }
export interface DataSource extends JsonObject { type: string; options?: JsonObject; }
export interface StudioDefinition extends JsonObject {
  title?: string; description?: string;
  visualizations: Record<string, Visualization>;
  dataSources?: Record<string, DataSource>;
  layout: JsonObject;
}
export interface Revision { number: number; definition: StudioDefinition; }
export type Edit = { type: 'rename'; title: string } | { type: 'tile-title'; id: string; title: string } | { type: 'compare' };

const object = (value: unknown): value is JsonObject => value !== null && typeof value === 'object' && !Array.isArray(value);
export function validateDefinition(value: unknown): StudioDefinition {
  if (!object(value) || !object(value.visualizations) || !object(value.layout)) throw new Error('Choose a Dashboard Studio JSON definition.');
  if (JSON.stringify(value).length > 1_000_000) throw new Error('This preview supports definitions up to 1 MB.');
  const visit = (node: unknown, depth = 0) => {
    if (depth > 60) throw new Error('The definition is nested too deeply.');
    if (object(node)) for (const [key, child] of Object.entries(node)) {
      if (['__proto__', 'constructor', 'prototype'].includes(key)) throw new Error('The definition contains an unsafe property.');
      visit(child, depth + 1);
    }
    else if (Array.isArray(node)) node.forEach(child => visit(child, depth + 1));
  };
  visit(value);
  for (const viz of Object.values(value.visualizations)) {
    if (!object(viz) || typeof viz.type !== 'string') throw new Error('A visualization is missing its type.');
    if (object(viz.dataSources)) for (const source of Object.values(viz.dataSources)) {
      if (typeof source !== 'string' || !object(value.dataSources) || !Object.hasOwn(value.dataSources, source)) throw new Error('A visualization refers to a missing data source.');
    }
  }
  return value as StudioDefinition;
}
export function cleanDashboardUrl(value: string): string {
  const url = new URL(value);
  for (const key of [...url.searchParams.keys()]) if (['tab', 'draft', 'focus'].includes(key) || key.startsWith('form.')) url.searchParams.delete(key);
  return url.href;
}
export const createStarter = () => structuredClone(validateDefinition(starter));
export const createBlank = (): StudioDefinition => ({
  title: 'New dashboard', description: '', visualizations: {}, dataSources: {}, inputs: {}, defaults: {}, expressions: {},
  layout: { globalInputs: [], tabs: { items: [{ label: 'Overview', layoutId: 'layout_main' }] },
    layoutDefinitions: { layout_main: { type: 'absolute', options: { width: 1200, height: 800, display: 'auto-scale' }, structure: [] } } },
});

export function applyEdit(revision: Revision, expectedRevision: number, edit: Edit): Revision {
  if (expectedRevision !== revision.number) throw new Error('This dashboard has changed. Retry the edit against the current revision.');
  const definition = structuredClone(revision.definition);
  if (edit.type === 'rename') {
    if (!edit.title.trim() || edit.title.length > 160) throw new Error('Use a title between 1 and 160 characters.');
    definition.title = edit.title.trim();
  }
  if (edit.type === 'tile-title') {
    if (!Object.hasOwn(definition.visualizations, edit.id)) throw new Error('The selected visualization no longer exists.');
    if (!edit.title.trim() || edit.title.length > 160) throw new Error('Use a title between 1 and 160 characters.');
    definition.visualizations[edit.id].title = edit.title.trim();
  }
  if (edit.type === 'compare') {
    const source = definition.dataSources?.ds_latency;
    if (source?.type !== 'ds.test' || !source.options || !object(source.options.data)) throw new Error('This example comparison is available on the starter dashboard.');
    const data = source.options.data as { fields: Array<{ name: string }>; columns: Array<Array<number | string>> };
    if (!data.fields.some(field => field.name === 'last_week_ms')) {
      data.fields.push({ name: 'last_week_ms' });
      data.columns.push(data.columns[0].map((_, i) => String(280 + (i % 5) * 9)));
    }
  }
  return { number: revision.number + 1, definition: validateDefinition(definition) };
}

export function applyEdits(revision: Revision, expectedRevision: number, edits: Edit[]): Revision {
  if (expectedRevision !== revision.number) throw new Error('This dashboard has changed. Retry the edit against the current revision.');
  let draft = revision;
  for (const edit of edits) draft = applyEdit(draft, draft.number, edit);
  return { number: revision.number + 1, definition: draft.definition };
}

export function previewDefinition(definition: StudioDefinition, results: Record<string, { fields: Array<{ name: string }>; columns: unknown[][] }> = {}, tokens?: {default?:Record<string,unknown>}, messages: Record<string, string> = {}, inputDefaults: InputDefaults = {}): StudioDefinition {
  const preview = structuredClone(definition);
  // Framework initialization gives static defaults precedence over initial bindings.
  // Mirror current values only in the preview clone so result refreshes and reopen
  // preserve the current filter without changing native export defaults.
  initializePreviewDefaults(preview, definition, tokens, inputDefaults);
  // Loading an imported document must never execute its queries or external links.
  for (const [id, source] of Object.entries(preview.dataSources || {})) if (source.type !== 'ds.test') {
    preview.dataSources![id] = results[id] ? { type: 'ds.test', options: { data: results[id], query: previewDependencyQuery(definition,id) } } : { type: 'ds.test', options: { data: { fields: [], columns: [] }, query: previewDependencyQuery(definition,id) } };
  }
  // Missing search results are a waiting state, not a native source error. Keep
  // labels/layout visible without a red error or a misleading empty chart.
  for (const [id, visualization] of Object.entries(preview.visualizations)) {
    const sourceId = visualization.dataSources?.primary;
    if (sourceId && definition.dataSources?.[sourceId]?.type !== 'ds.test' && !results[sourceId]) {
      const source = definition.dataSources?.[sourceId];
      const nativeOnly = source && !['ds.search', 'ds.spl2', 'ds.chain', 'ds.savedSearch'].includes(source.type);
      preview.visualizations[id] = { type: 'splunk.markdown', title: visualization.title,
        options: { markdown: nativeOnly ? 'Open this dashboard in native Studio to run this source type. Its configuration is preserved.' : messages[sourceId] || 'Search results pending.' } };
    }
  }
  const stripExternalActions = (node: unknown) => {
    if (Array.isArray(node)) { node.forEach(stripExternalActions); return; }
    if (!object(node)) return;
    if (Array.isArray(node.eventHandlers)) node.eventHandlers = node.eventHandlers.filter(handler => object(handler) && ['drilldown.setToken', 'drilldown.switchToTab', 'drilldown.setTimeRange', 'drilldown.resetTokens', 'drilldown.unsetTokens'].includes(String(handler.type)));
    for (const [key, child] of Object.entries(node)) {
      if (['src', 'href', 'url'].includes(key) && typeof child === 'string') { if (key !== 'src' || !previewImage(child)) delete node[key]; }
      else if (key === 'markdown' && typeof child === 'string') node[key] = child.replace(/!\[[^\]]*\]\([^)]*\)/g, '[Image omitted in preview]').replace(/\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/<[^>]+>/g, '');
      else stripExternalActions(child);
    }
  };
  stripExternalActions(preview);
  return preview;
}

const xmlEscape = (value: string) => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
export function toStudioXml(definition: StudioDefinition, theme: 'light' | 'dark'): string {
  const json = JSON.stringify(validateDefinition(definition), null, 2).replace(/\]\]>/g, ']]]]><![CDATA[>');
  return `<dashboard version="2" theme="${theme}"><label>${xmlEscape(definition.title || 'Untitled dashboard')}</label><description>${xmlEscape(definition.description || '')}</description><definition><![CDATA[${json}]]></definition></dashboard>`;
}

export function fromStudioXml(xml: string): StudioDefinition {
  const parsed = new DOMParser().parseFromString(xml, 'application/xml');
  if (parsed.querySelector('parsererror') || parsed.documentElement.getAttribute('version') !== '2') throw new Error('Choose a Dashboard Studio dashboard.');
  const json = parsed.querySelector('definition')?.textContent;
  if (!json) throw new Error('This dashboard has no Studio definition.');
  return validateDefinition(JSON.parse(json));
}
