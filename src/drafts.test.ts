import { describe, expect, it, vi } from 'vitest';
import { DraftSync, newDraftId, type DraftRecord, type DraftSnapshot } from './drafts';
import { createBlank } from './document';

const state = (prompt = ''): DraftSnapshot => ({ definition: createBlank(), messages: [{ id: 1, user: true, text: 'Use Splunk data' }],
  prompt, attachments: [], selected: '', suggestions: [], activity: [], saved: null, searchesEnabled: true,
  dataContext: { index: 'orders', earliest: '-24h' } });
const record = (id: string, version: number, snapshot: DraftSnapshot) => ({ id, version, state: snapshot } as DraftRecord);

describe('durable draft writes', () => {
  it('supports HTTP Splunk origins without the secure-context randomUUID API', () => {
    vi.stubGlobal('crypto', { getRandomValues: (bytes: Uint8Array) => bytes.fill(171) });
    try { expect(newDraftId()).toBe('ab'.repeat(16)); } finally { vi.unstubAllGlobals(); }
  });
  it('serializes writes with the newly returned version and captures each snapshot', async () => {
    const calls: Array<{ version: number; state: DraftSnapshot }> = [];
    let release!: () => void;
    const barrier = new Promise<void>(resolve => { release = resolve; });
    const sync = new DraftSync(async (id, version, snapshot) => {
      calls.push({ version, state: snapshot });
      if (version === 0) await barrier;
      return record(id, version + 1, snapshot);
    });
    const first = state('first');
    const one = sync.save('draft', first); first.prompt = 'outside mutation';
    const two = sync.save('draft', state('second'));
    release(); await Promise.all([one, two]);
    expect(calls.map(call => call.version)).toEqual([0, 1]);
    expect(calls.map(call => call.state.prompt)).toEqual(['first', 'second']);
    expect(sync.matches('draft', state('second'))).toBe(true);
  });
  it('retains the last confirmed version after a failed save and never hides a conflict', async () => {
    const versions: number[] = [];
    const sync = new DraftSync(async (id, version, snapshot) => {
      versions.push(version);
      if (snapshot.prompt === 'conflict') throw new Error('Changed in another session');
      return record(id, version + 1, snapshot);
    });
    sync.adopt(record('draft', 7, state('saved')));
    await expect(sync.save('draft', state('conflict'))).rejects.toThrow('another session');
    expect(sync.matches('draft', state('conflict'))).toBe(false);
    await sync.save('draft', state('retry'));
    expect(versions).toEqual([7, 7]);
  });
  it('restores exact conversation/context and keeps an empty proposal list distinct from local fallbacks', async () => {
    let writes = 0;
    const sync = new DraftSync(async (id, version, snapshot) => { writes++; return record(id, version + 1, snapshot); });
    const restored = state(); sync.adopt(record('draft', 3, restored));
    await sync.save('draft', restored); expect(writes).toBe(0);
    expect(sync.matches('draft', { ...restored, suggestions: null })).toBe(false);
    expect(sync.matches('draft', { ...restored, dataContext: { index: 'other', earliest: '-24h' } })).toBe(false);
  });
});
