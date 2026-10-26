import type { PromptSuggestion } from './prompts';
import type { DashboardBrief } from './drafts';
import type { DataProfile, DataScope } from './data';
import type { TokenState } from '@splunk/dashboard-types';
import { validateDefinition, type JsonObject, type Revision, type StudioDefinition } from './document';

export interface StudioChange { op: 'set' | 'remove'; path: string; value: string; }
export interface Attachment { name: string; data: string; }
export interface AgentReply { brief?: DashboardBrief; revision: number; message: string; changes: StudioChange[]; suggestions: PromptSuggestion[]; repaired: boolean; activity: string[]; validationNotes?: string[]; recovery?: { modelCalls: number; queryChecks: number }; pagePurposes?: Record<string,string>; dataContext?: DataScope | null; dataProfile?: DataProfile | null; searchReceipts?: Array<{ source: string; fields: string[]; rows: number; earliest: string }>; }
export interface Environment {
  version: string; studioVersion: string; spl: string;
  spl2: { adhoc: string; modules: string };
  features: Record<string, boolean>; visualizations: string[];
  preview: { rows: number; seconds: number; timeRange: string; externalNavigation: string; customVisualizations: string };
}
export interface SearchResult { state: 'complete' | 'partial'; evidence: { state: 'complete' | 'partial'; checkedAt: string; reasons: string[]; resultCount: number | null; finalized: boolean; earliest: string; latest: string }; fields: Array<{ name: string }>; results: Array<Record<string, unknown>>; language: string; bounded: boolean; warning: string; }
export interface PreviewRows { fields: Array<{ name: string }>; columns: unknown[][]; }

const unsafe = new Set(['__proto__', 'constructor', 'prototype']);
const roots = new Set(['title', 'description', 'visualizations', 'dataSources', 'inputs', 'layout', 'defaults', 'expressions', 'applicationProperties']);
export function applyStudioChanges(revision: Revision, reply: Pick<AgentReply, 'revision' | 'changes'>): Revision {
  if (revision.number !== reply.revision) throw new Error('The dashboard changed while the agent was working. Retry against the current draft.');
  if (!Array.isArray(reply.changes) || reply.changes.length > 64) throw new Error('The agent returned too many changes.');
  const definition = structuredClone(revision.definition);
  for (const change of reply.changes) {
    if (!['set', 'remove'].includes(change.op) || typeof change.path !== 'string' || !change.path.startsWith('/') || /~(?![01])/.test(change.path)) throw new Error('The agent returned an invalid edit.');
    const parts = change.path.slice(1).split('/').map(part => part.replace(/~1/g, '/').replace(/~0/g, '~'));
    if (!roots.has(parts[0]) || parts.some(part => unsafe.has(part))) throw new Error('The edit is outside the Studio document.');
    let target: JsonObject | unknown[] = definition;
    for (const part of parts.slice(0, -1)) {
      if (!Object.hasOwn(target, part)) throw new Error('An edit parent no longer exists.');
      const next: unknown = Reflect.get(target, part);
      if (!next || typeof next !== 'object') throw new Error('An edit parent is invalid.');
      target = next as JsonObject | unknown[];
    }
    const key = parts.at(-1)!;
    if (change.op === 'set') {
      if (typeof change.value !== 'string' || change.value.length > 500_000 || (Array.isArray(target) && key !== '-' && (!/^\d+$/.test(key) || Number(key) > target.length))) throw new Error('The edit value or array position is invalid.');
      const value: unknown = JSON.parse(change.value);
      if (Array.isArray(target) && (key === '-' || Number(key) === target.length)) target.push(value);
      else Reflect.set(target, key, value);
    } else {
      if (!Object.hasOwn(target, key)) throw new Error('The property to remove does not exist.');
      if (Array.isArray(target) && !/^\d+$/.test(key)) throw new Error('The array position is invalid.');
      if (Array.isArray(target)) target.splice(Number(key), 1); else Reflect.deleteProperty(target, key);
    }
  }
  validateDefinition(definition);
  return { number: revision.number + 1, definition };
}

export async function readAttachment(file: File): Promise<Attachment> {
  if (!['image/png', 'image/jpeg', 'image/webp', 'application/pdf'].includes(file.type) || file.size > 4_000_000 || file.size === 0) throw new Error('Choose a PNG, JPEG, WebP, or PDF under 4 MB.');
  const data = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('The attachment could not be read.'));
    reader.readAsDataURL(file);
  });
  return { name: file.name.slice(0, 200), data };
}

export function searchRequest(definition: StudioDefinition, id: string, tokens?: TokenState): { query: string; language: 'spl' | 'spl2'; key: string } {
  const seen = new Set<string>();
  const resolve = (sourceId: string): { query: string; language: 'spl' | 'spl2' } => {
    if (seen.has(sourceId)) throw new Error('A chain search contains a cycle.');
    seen.add(sourceId);
    const source = definition.dataSources?.[sourceId];
    const query = source?.options?.query;
    if (!source || typeof query !== 'string' || !['ds.search', 'ds.spl2', 'ds.chain'].includes(source.type)) throw new Error('This source requires native Studio or a query before it can run.');
    if (source.type === 'ds.chain') {
      const parent = resolve(String(source.options?.extend || source.extend || ''));
      return { query: parent.query + ' | ' + query.replace(/^\s*\|/, ''), language: parent.language };
    }
    return { query, language: source.type === 'ds.spl2' ? 'spl2' : 'spl' };
  };
  const result = resolve(id);
  if (/["']\$[A-Za-z0-9_.:-]+\|s\$["']/.test(result.query)) throw new Error('The |s token filter already adds quotes. Remove surrounding quotes in the source query.');
  const defaults = definition.defaults as {tokens?:{default?:Record<string,{value:unknown}>}} | undefined;
  const values: Record<string, unknown> = { ...Object.fromEntries(Object.entries(defaults?.tokens?.default || {}).map(([key,value])=>[key,value.value])), ...tokens?.default };
  for (const input of Object.values((definition.inputs || {}) as Record<string, { options?: { token?: string; defaultValue?: string } }>)) {
    if (input.options?.token && !Object.hasOwn(values, input.options.token)) values[input.options.token] = input.options.defaultValue;
  }
  result.query = result.query.replace(/\$([A-Za-z0-9_.:-]+)(\|s)?\$/g, (_whole, token: string, quote?: string) => {
    const raw = values[token];
    const items = Array.isArray(raw) ? raw : [raw];
    if (!items.length || items.some(value => !['string', 'number', 'boolean'].includes(typeof value))) throw new Error(`Choose a value for ${token} before running its search.`);
    const strings = items.map(value => String(value));
    if (quote) return strings.map(value => JSON.stringify(value)).join(',');
    if (strings.some(value => !/^[A-Za-z0-9_.:-]+$/.test(value))) throw new Error(`Use the |s token filter for ${token} in this query.`);
    return strings.join(',');
  });
  return { ...result, key: JSON.stringify(result) };
}

export const resultRows = (result: SearchResult): PreviewRows => ({ fields: result.fields,
  columns: result.fields.map(field => result.results.map(row => row[field.name] ?? null)) });
