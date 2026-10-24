import { afterEach, describe, expect, it, vi } from 'vitest';
import { createBlank, fromStudioXml } from './document';
import { listDashboards, listDestinationApps, providerRequest, saveCopy } from './api';

vi.mock('@splunk/splunk-utils/url', () => ({ createRESTURL: (endpoint: string, { app, owner }: { app: string; owner: string }) => `https://example.test/servicesNS/${owner}/${app}/${endpoint}`, createURL: (path: string) => `https://example.test/${path}` }));
vi.mock('@splunk/splunk-utils/fetch', () => ({ createFetchInit: (init: RequestInit) => init }));
vi.mock('./document', async importOriginal => ({ ...await importOriginal<typeof import('./document')>(), fromStudioXml: vi.fn() }));
const json = (body: unknown) => new Response(JSON.stringify(body));
const context = { entry: [{ content: { username: 'fixture-user' } }] };
const install = (handler: (url: string, init?: RequestInit) => Response) => {
  vi.stubGlobal('window', { location: { pathname: '/en-US/app/constellation/workspace', protocol: 'https:' } });
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => handler(url, init));
  vi.stubGlobal('fetch', fetcher); return fetcher;
};
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });
describe('native dashboard handoff', () => {
  it('creates and reads back in the selected app under the current owner, preserving the definition', async () => {
    const definition = { ...createBlank(), title: 'Handoff', futureProperty: { retained: true } };
    vi.mocked(fromStudioXml).mockReturnValue(definition);
    const fetcher = install((url, init) => url.includes('current-context') ? json(context) : init?.method === 'POST' ? json({ entry: [] }) : json({ entry: [{ acl: { sharing: 'user', owner: 'fixture-user', app: 'search' }, content: { 'eai:data': 'fixture-xml' } }] }));
    const saved = await saveCopy(definition, 'dark', 'search');
    expect(saved.url).toMatch(/\/app\/search\/constellation_[a-f0-9]{24}$/);
    const calls = fetcher.mock.calls.filter(([url]) => url.includes('data/ui/views'));
    expect(calls).toHaveLength(2);
    expect(calls.every(([url]) => url.includes('/fixture-user/search/data/ui/views'))).toBe(true);
    const xml = (calls[0][1]?.body as URLSearchParams).get('eai:data');
    expect(xml).toContain('version="2" theme="dark"'); expect(xml).toContain('futureProperty'); expect(definition.futureProperty.retained).toBe(true);
  });
  it('rejects an invalid app before creating a dashboard', async () => {
    const fetcher = install(() => json(context));
    await expect(saveCopy(createBlank(), 'light', '../search')).rejects.toThrow('valid destination');
    expect(fetcher.mock.calls.filter(([url]) => url.includes('data/ui/views'))).toHaveLength(0);
  });
  it('does not report a nonprivate or mismatched readback as success', async () => {
    let sharing = 'app';
    install((url, init) => url.includes('current-context') ? json(context) : init?.method === 'POST' ? json({ entry: [] }) : json({ entry: [{ acl: { sharing, owner: 'fixture-user', app: 'constellation' }, content: { 'eai:data': 'fixture-xml' } }] }));
    await expect(saveCopy(createBlank(), 'light')).rejects.toThrow('private sharing');
    sharing = 'user'; vi.mocked(fromStudioXml).mockReturnValue({ ...createBlank(), title: 'Different' });
    await expect(saveCopy(createBlank(), 'light')).rejects.toThrow('differs');
  });
  it('lists views beyond the first page and leaves shared objects unmanaged', async () => {
    const entry = (i: number) => ({ name: `fixture_${i}`, content: { label: `Dashboard ${i}`, 'eai:data': '<dashboard version="2">' }, acl: { app: 'constellation', owner: 'fixture-user', sharing: i === 100 ? 'app' : 'user' } });
    install(url => url.includes('current-context') ? json(context) : json({ entry: url.includes('offset=100') ? [entry(100)] : Array.from({ length: 100 }, (_, i) => entry(i)), paging: { total: 101 } }));
    const list = await listDashboards(); expect(list).toHaveLength(101); expect(list[100].canManage).toBe(false); expect(list[0].canManage).toBe(true);
  });
  it('offers enabled visible destination apps', async () => {
    install(() => json({ entry: [{ name: 'search', content: { label: 'Search & Reporting', visible: true, disabled: false } }, { name: 'disabled', content: { disabled: true } }, { name: 'hidden', content: { visible: false } }] }));
    expect(await listDestinationApps()).toEqual([{ name: 'search', label: 'Search & Reporting' }]);
  });
  it('explains a lost session as an app-service failure', async () => {
    install(() => new Response('<html>login</html>'));
    await expect(providerRequest('drafts')).rejects.toThrow('Splunk session');
  });
});
