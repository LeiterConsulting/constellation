import { describe, expect, it } from 'vitest';
import { DraftRecovery } from './draftRecovery';
import { DraftSync, type DraftRecord, type DraftSnapshot } from './drafts';
import { createBlank } from './document';
const id = 'a'.repeat(32);
const state = (prompt = ''): DraftSnapshot => ({ definition: createBlank(), messages: [{ id: 1, user: true, text: 'Use actual observations' }], prompt, attachments: [], selected: '', suggestions: [], activity: [], saved: null, searchesEnabled: true, activeTab: 'layout_main' });
const record = (version: number, snapshot = state()) => ({ id, version, state: snapshot } as DraftRecord);
function storage() {
  const map = new Map<string, string>();
  return { map, getItem: (key: string) => map.get(key) || null, setItem: (key: string, value: string) => { map.set(key, value); }, removeItem: (key: string) => { map.delete(key); } };
}
describe('pending draft refresh recovery', () => {
  it('recovers changes before the debounce or first save, including conversation and page state', () => {
    const store = storage(), journal = new DraftRecovery(() => store);
    const pending = { ...state('Keep this request'), activeTab: 'layout_details', pendingRequest: 'Interrupted request' };
    expect(journal.checkpoint('alice', id, 0, pending)).toBe(true);
    const refreshed = new DraftRecovery(() => store).restore('alice', id, null);
    expect(refreshed).toMatchObject({ pending: true, record: { version: 0, state: pending } });
    // Recovery produces a draft, not an author dispatch or an accepted model reply.
    const sync = new DraftSync(); sync.resume(id, refreshed!.record.version);
    expect(sync.matches(id, pending)).toBe(false);
  });
  it('confirms an already committed save and removes the pending copy', () => {
    const store = storage(), journal = new DraftRecovery(() => store);
    journal.checkpoint('alice', id, 3, state('latest'));
    expect(journal.restore('alice', id, record(4, state('latest')))).toEqual({ pending: false, record: record(4, state('latest')) });
    expect(store.map.size).toBe(0);
  });
  it('advances only an exact in-flight intermediate save before saving newer local changes', () => {
    const store = storage(), journal = new DraftRecovery(() => store);
    journal.checkpoint('alice', id, 3, state('newer'), { version: 3, state: state('in flight') });
    expect(journal.restore('alice', id, record(4, state('in flight')))).toMatchObject({ pending: true, record: { version: 4, state: state('newer') } });
    expect(journal.restore('alice', id, record(5, state('in flight')))).toMatchObject({ pending: true, record: { version: 3 } });
  });
  it('retains the old revision when another session changed the server', async () => {
    const journal = new DraftRecovery(() => storage());
    // Use one actual store across the refresh.
    const store = storage(), recovery = new DraftRecovery(() => store);
    recovery.checkpoint('alice', id, 3, state('local'));
    const result = recovery.restore('alice', id, record(4, state('other tab')))!;
    const sync = new DraftSync(async (_id, version) => { expect(version).toBe(3); throw new Error('another session'); });
    sync.resume(id, result.record.version);
    await expect(sync.save(id, result.record.state)).rejects.toThrow('another session');
    expect(sync.matches(id, result.record.state)).toBe(false);
    expect(journal.restore('alice', id, null)).toBeNull();
  });
  it('cannot resurrect a deleted or unavailable existing draft', () => {
    const store = storage(), journal = new DraftRecovery(() => store);
    journal.checkpoint('alice', id, 0, state()); expect(journal.restore('alice', id, null, true)).toBeNull();
    journal.checkpoint('alice', id, 2, state()); expect(journal.restore('alice', id, null)).toBeNull();
    expect(store.map.size).toBe(0);
  });
  it('does not restore a previous account, another draft, expired or malformed content', () => {
    const store = storage(); let time = 0; const journal = new DraftRecovery(() => store, () => time);
    journal.checkpoint('alice', id, 2, state()); expect(journal.restore('bob', id, null)).toBeNull(); expect(store.map.size).toBe(0);
    journal.checkpoint('alice', id, 2, state()); expect(journal.restore('alice', 'b'.repeat(32), null)).toBeNull();
    time = 7 * 60 * 60 * 1000; expect(journal.restore('alice', id, record(2))).toMatchObject({ pending: false }); expect(store.map.size).toBe(0);
    store.setItem('constellation.pendingDraft.v1', '{'); expect(journal.restore('alice', id, null)).toBeNull(); expect(store.map.size).toBe(0);
  });
  it('fails closed on quota, oversized snapshots and disabled storage, discarding stale pending content', () => {
    const store = storage(), journal = new DraftRecovery(() => store);
    journal.checkpoint('alice', id, 0, state());
    expect(journal.checkpoint('alice', id, 0, state('x'.repeat(1_500_000)))).toBe(false); expect(store.map.size).toBe(0);
    const unavailable = new DraftRecovery(() => { throw new Error('Storage blocked'); });
    expect(unavailable.checkpoint('alice', id, 0, state())).toBe(false); expect(unavailable.restore('alice', id, null)).toBeNull();
  });
  it('copies only draft properties and does not erase another active draft on a late save', () => {
    const store = storage(), journal = new DraftRecovery(() => store);
    journal.checkpoint('alice', id, 0, { ...state(), apiKey: 'synthetic-sensitive-setting' } as DraftSnapshot);
    expect([...store.map.values()][0]).not.toContain('synthetic-sensitive-setting');
    journal.clear('b'.repeat(32)); expect(store.map.size).toBe(1);
    journal.clear(id); expect(store.map.size).toBe(0);
  });
});
