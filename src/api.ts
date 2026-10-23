import { createFetchInit } from '@splunk/splunk-utils/fetch';
import { createRESTURL, createURL } from '@splunk/splunk-utils/url';
import { fromStudioXml, toStudioXml, type StudioDefinition } from './document';

export const isSplunk = () => window.location.pathname.includes('/app/constellation/');
export const secureSettingsOrigin = () => window.location.protocol === 'https:' || ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
export type ProviderName = 'openai' | 'ollama' | 'aitk';
export const providerLabel = (provider?: ProviderName) => provider === 'aitk' ? 'Splunk AITK' : provider === 'ollama' ? 'Ollama' : 'OpenAI';
export interface ProviderSettings { provider: ProviderName; configured: boolean; connection?: string; connections?: Partial<Record<ProviderName, { model?: string; keyConfigured?: boolean; base_url?: string; connection?: string }>>; baseUrl: string; model: string; keyConfigured: boolean; capabilities?: { images: boolean; pdf: boolean; reason: string; source: string }; }
export async function providerRequest<T>(action: 'settings' | 'models' | 'test' | 'assist' | 'author' | 'environment' | 'datasets' | 'preview' | 'drafts' | 'library' | 'discovery' | 'profile', body?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  if (!isSplunk()) throw new Error('Open the installed Splunk app to configure a provider.');
  if (action === 'settings' && body?.apiKey && !secureSettingsOrigin()) throw new Error('Open Splunk through HTTPS before saving a provider key.');
  const url = createRESTURL(`constellation/v1/${action}`, { app: 'constellation', owner: '-' });
  const response = await fetch(url, createFetchInit({ method: body ? 'POST' : 'GET',
    body: body ? JSON.stringify(body) : undefined, headers: body ? { 'Content-Type': 'application/json' } : {}, signal }));
  let result: T & { error?: string; validationError?: string; code?: string };
  try { result = await response.json(); } catch { throw new Error('The provider service is unavailable. Check that the updated app backend is loaded.'); }
  if (!response.ok || result.error) {
    const failure: Error & { validationError?: string; code?: string } = new Error(result.error || `The app service returned HTTP ${response.status}.`);
    failure.code = result.code;
    if (typeof result.validationError === 'string') failure.validationError = result.validationError;
    throw failure;
  }
  return result;
}
interface Entry { name: string; content: Record<string, unknown>; acl?: { app?: string; sharing?: string; owner?: string }; }
interface ResponseBody { entry: Entry[]; }
async function request(endpoint: string, owner = '-', fields?: URLSearchParams): Promise<ResponseBody> {
  if (!isSplunk()) throw new Error('Open the installed Splunk app to use this action.');
  const url = createRESTURL(endpoint, { app: 'constellation', owner });
  const response = await fetch(`${url}${url.includes('?') ? '&' : '?'}output_mode=json&count=100`, createFetchInit({
    method: fields ? 'POST' : 'GET', body: fields,
    headers: fields ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {},
  }));
  if (!response.ok) throw new Error(`Splunk returned HTTP ${response.status}. The current draft is preserved.`);
  return response.json();
}

export async function listDashboards() {
  const [result, context] = await Promise.all([request('data/ui/views'), request('authentication/current-context')]);
  return result.entry.filter(entry => entry.acl?.app === 'constellation' && typeof entry.content['eai:data'] === 'string' && /<dashboard[^>]+version=["']2["']/.test(String(entry.content['eai:data'])))
    .map(entry => ({ name: entry.name, title: String(entry.content.label || entry.name), xml: String(entry.content['eai:data']),
      canManage: entry.acl?.owner === context.entry[0]?.content.username && entry.acl?.sharing === 'user' }));
}
export async function saveCopy(definition: StudioDefinition, theme: 'light' | 'dark') {
  const context = await request('authentication/current-context');
  const username = context.entry[0]?.content.username;
  if (typeof username !== 'string' || !username) throw new Error('The current Splunk user could not be determined.');
  const name = 'constellation_' + Array.from(crypto.getRandomValues(new Uint8Array(12)), byte => byte.toString(16).padStart(2, '0')).join('');
  await request('data/ui/views', username, new URLSearchParams({ name, 'eai:data': toStudioXml(definition, theme) }));
  const saved = await request(`data/ui/views/${encodeURIComponent(name)}`, username);
  if (saved.entry[0]?.acl?.sharing !== 'user') throw new Error('The view was created, but its private sharing could not be verified. Inspect its permissions in Splunk.');
  const xml = saved.entry[0]?.content['eai:data'];
  if (typeof xml !== 'string') throw new Error('Splunk saved the view but its definition could not be read back.');
  const restored = fromStudioXml(xml);
  if (JSON.stringify(restored) !== JSON.stringify(definition)) throw new Error('The saved definition differs from the draft. Inspect it in native Studio.');
  return { name, url: createURL(`app/constellation/${name}`) };
}
