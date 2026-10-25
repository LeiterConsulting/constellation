import { createFetchInit } from '@splunk/splunk-utils/fetch';
import { createRESTURL, createURL } from '@splunk/splunk-utils/url';
import { fromStudioXml, toStudioXml, type StudioDefinition } from './document';
import { fetchWithDeadline } from './requestTimeout';

export const isSplunk = () => window.location.pathname.includes('/app/constellation/');
export const secureSettingsOrigin = () => window.location.protocol === 'https:' || ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
export type ProviderName = 'openai' | 'ollama' | 'aitk';
export const providerLabel = (provider?: ProviderName) => provider === 'aitk' ? 'Splunk AITK' : provider === 'ollama' ? 'Ollama' : 'OpenAI';
interface RecoveryStats { modelCalls: number; queryChecks: number; seconds: number; }
type ProviderFailure = Error & { validationError?: string; code?: string; recovery?: RecoveryStats };
export function failureActivity(error: unknown): string[] {
  if (!(error instanceof Error)) return [];
  const failure = error as ProviderFailure;
  return [...(failure.validationError ? [failure.validationError] : []), ...(failure.recovery ? [
    `${failure.recovery.modelCalls} model requests · ${failure.recovery.queryChecks} search checks · ${Math.round(failure.recovery.seconds)} seconds. Previous dashboard preserved.`,
  ] : [])];
}
export interface ModelReadinessReport { limits: { label: string; value: string }[]; warnings: string[]; scope: string; tested: boolean; usage: { input_tokens?: number; output_tokens?: number; reasoning_tokens?: number }; }
export interface ProviderSettings { provider: ProviderName; configured: boolean; readiness?: ModelReadinessReport; connection?: string; aitkAccess?: { available: boolean; connection: string; unavailable?: boolean } | null; connections?: Partial<Record<ProviderName, { model?: string; keyConfigured?: boolean; base_url?: string; connection?: string }>>; baseUrl: string; model: string; keyConfigured: boolean; keyStorage?: { canWrite: boolean } | null; capabilities?: { images: boolean; pdf: boolean; reason: string; source: string }; }
export async function providerRequest<T>(action: 'settings' | 'models' | 'test' | 'assist' | 'author' | 'run' | 'environment' | 'datasets' | 'preview' | 'drafts' | 'library' | 'discovery' | 'profile' | 'preview_job', body?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  if (!isSplunk()) throw new Error('Open the installed Splunk app to configure a provider.');
  if (action === 'settings' && body?.apiKey && !secureSettingsOrigin()) throw new Error('Open Splunk through HTTPS before saving a provider key.');
  const url = createRESTURL(`constellation/${action === 'run' ? 'control' : 'v1'}/${action}`, { app: 'constellation', owner: '-' });
  const { response, result } = await fetchWithDeadline(url, createFetchInit({ method: body ? 'POST' : 'GET',
    body: body ? JSON.stringify(body) : undefined, headers: body ? { 'Content-Type': 'application/json' } : {}, signal }), ['author', 'test'].includes(action) ? 240_000 : 30_000, async response => {
    let result: T & { error?: string; validationError?: string; code?: string; recovery?: Record<string, unknown> };
    try { result = await response.json(); } catch (failure) { if (failure instanceof SyntaxError) throw new Error('The app service is unavailable. Check your Splunk session and try again.'); throw failure; }
    return { response, result };
  });
  if (!response.ok || result.error) {
    const failure: ProviderFailure = new Error(result.error || `The app service returned HTTP ${response.status}.`);
    failure.code = result.code;
    if (typeof result.validationError === 'string') failure.validationError = result.validationError;
    const evidence = result.recovery;
    if (evidence && ['modelCalls', 'queryChecks', 'seconds'].every(key => typeof evidence[key] === 'number' && Number.isFinite(evidence[key]) && Number(evidence[key]) >= 0)) {
      failure.recovery = { modelCalls: Number(evidence.modelCalls), queryChecks: Number(evidence.queryChecks), seconds: Number(evidence.seconds) };
    }
    throw failure;
  }
  return result;
}
interface Entry { name: string; content: Record<string, unknown>; acl?: { app?: string; sharing?: string; owner?: string }; }
interface ResponseBody { entry: Entry[]; paging?: { total: number; }; }
async function request(endpoint: string, owner = '-', fields?: URLSearchParams, app = 'constellation', offset = 0): Promise<ResponseBody> {
  if (!isSplunk()) throw new Error('Open the installed Splunk app to use this action.');
  if (!/^[A-Za-z0-9_.-]{1,150}$/.test(app) || app === '.' || app === '..') throw new Error('Choose a valid destination app.');
  const url = createRESTURL(endpoint, { app, owner });
  return fetchWithDeadline(`${url}${url.includes('?') ? '&' : '?'}output_mode=json&count=100&offset=${offset}`, createFetchInit({
    method: fields ? 'POST' : 'GET', body: fields,
    headers: fields ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {},
  }), 20_000, async response => {
    if (!response.ok) throw new Error(`Splunk returned HTTP ${response.status}. The current draft is preserved.`);
    return response.json();
  });
}

async function entries(endpoint: string) {
  const all: Entry[] = [];
  for (let offset = 0; offset < 5000; offset += 100) {
    const page = await request(endpoint, '-', undefined, 'constellation', offset);
    all.push(...page.entry);
    if (page.entry.length < 100 || (page.paging && all.length >= page.paging.total)) return all;
  }
  throw new Error('This list exceeds 5,000 entries. Use Splunk’s dashboard manager to find a view.');
}

export async function listDestinationApps() {
  return (await entries('apps/local')).filter(entry => !entry.content.disabled && entry.content.visible !== false)
    .map(entry => ({ name: entry.name, label: String(entry.content.label || entry.name) }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export async function listDashboards() {
  const [result, context] = await Promise.all([entries('data/ui/views'), request('authentication/current-context')]);
  return result.filter(entry => entry.acl?.app === 'constellation' && typeof entry.content['eai:data'] === 'string' && /<dashboard[^>]+version=["']2["']/.test(String(entry.content['eai:data'])))
    .map(entry => ({ name: entry.name, title: String(entry.content.label || entry.name), xml: String(entry.content['eai:data']),
      url: createURL(`app/constellation/${encodeURIComponent(entry.name)}`),
      canManage: entry.acl?.owner === context.entry[0]?.content.username && entry.acl?.sharing === 'user' }));
}
export async function saveCopy(definition: StudioDefinition, theme: 'light' | 'dark', app = 'constellation') {
  const context = await request('authentication/current-context');
  const username = context.entry[0]?.content.username;
  if (typeof username !== 'string' || !username) throw new Error('The current Splunk user could not be determined.');
  const name = 'constellation_' + Array.from(crypto.getRandomValues(new Uint8Array(12)), byte => byte.toString(16).padStart(2, '0')).join('');
  await request('data/ui/views', username, new URLSearchParams({ name, 'eai:data': toStudioXml(definition, theme) }), app);
  const saved = await request(`data/ui/views/${encodeURIComponent(name)}`, username, undefined, app);
  if (saved.entry[0]?.acl?.sharing !== 'user' || saved.entry[0]?.acl?.owner !== username || saved.entry[0]?.acl?.app !== app) throw new Error('The view was created, but its private sharing could not be verified. Inspect its permissions in Splunk.');
  const xml = saved.entry[0]?.content['eai:data'];
  if (typeof xml !== 'string') throw new Error('Splunk saved the view but its definition could not be read back.');
  const restored = fromStudioXml(xml);
  if (JSON.stringify(restored) !== JSON.stringify(definition)) throw new Error('The saved definition differs from the draft. Inspect it in native Studio.');
  return { name, url: createURL(`app/${encodeURIComponent(app)}/${name}`) };
}
