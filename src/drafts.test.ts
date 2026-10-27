import { describe, expect, it, vi } from 'vitest';
import { DraftSync, newDraftId, type DraftRecord, type DraftSnapshot } from './drafts';
import { createBlank } from './document';
import { AppDeliveryError } from './restDelivery';

const state = (prompt = ''): DraftSnapshot => ({ definition: createBlank(), messages: [{ id: 1, user: true, text: 'Use Splunk data' }],
  prompt, attachments: [], selected: '', suggestions: [], activity: [], saved: null, searchesEnabled: true,
  dataContext: { index: 'orders', earliest: '-24h' } });
const record = (id: string, version: number, snapshot: DraftSnapshot) => ({ id, version, state: snapshot } as DraftRecord);

describe('durable draft writes', () => {
  it('rebases a definite conflict only onto the exact in-flight save recovered from this tab', async () => {
    const versions: number[] = [];
    const writer = vi.fn(async (id, version, snapshot) => {
      versions.push(version);
      if (version === 3) throw Object.assign(new Error('conflict'), { code: 'draft_conflict' });
      return record(id, version + 1, snapshot);
    });
    const sync = new DraftSync(writer, async () => record('draft', 4, state('old tab save')));
    sync.resume('draft', 3, { version: 3, state: state('old tab save') });
    await sync.save('draft', state('latest'));
    expect(versions).toEqual([3, 4]); expect(sync.matches('draft', state('latest'))).toBe(true);
    for (const other of [record('draft', 4, state('other tab')), record('draft', 5, state('old tab save'))]) {
      const guarded = new DraftSync(writer, async () => other);
      guarded.resume('draft', 3, { version: 3, state: state('old tab save') });
      await expect(guarded.save('draft', state('latest'))).rejects.toMatchObject({ code: 'draft_conflict' });
      expect(guarded.version('draft')).toBe(3);
    }
    expect(versions).toEqual([3, 4, 3, 3]);
  });
  it('confirms a lost save response by readback without replaying the write', async () => {
    const writer = vi.fn(async () => { throw new AppDeliveryError('lost response'); });
    const reader = vi.fn(async () => record('draft', 8, state('latest')));
    const sync = new DraftSync(writer, reader); sync.adopt(record('draft', 7, state()));
    await sync.save('draft', state('latest'));
    expect(writer).toHaveBeenCalledTimes(1); expect(reader).toHaveBeenCalledTimes(1);
    expect(sync.version('draft')).toBe(8); expect(sync.matches('draft', state('latest'))).toBe(true);
  });
  it('retains an uncertain issued write and never adopts different readback or a permission failure', async () => {
    const writer = vi.fn(async () => { throw new AppDeliveryError('lost response'); });
    const sync = new DraftSync(writer, async () => record('draft', 8, state('other session')));
    sync.adopt(record('draft', 7, state()));
    await expect(sync.save('draft', state('latest'))).rejects.toThrow('lost response');
    expect(writer).toHaveBeenCalledTimes(1); expect(sync.version('draft')).toBe(7);
    expect(sync.issued('draft')).toEqual({ version: 7, state: state('latest') });
    const reader = vi.fn(); const denied = new DraftSync(async () => { throw new Error('Permission denied'); }, reader);
    await expect(denied.save('draft', state())).rejects.toThrow('Permission denied'); expect(reader).not.toHaveBeenCalled();
  });
  it('isolates simultaneous authors and serializes rapid saves without losing the latest conversation', async () => {
    const versions = [0, 0, 0], confirmed: DraftSnapshot[] = [];
    const authors = versions.map((_, owner) => new DraftSync(async (id, version, snapshot) => {
      expect(version).toBe(versions[owner]); await Promise.resolve(); versions[owner]++;
      confirmed[owner] = snapshot; return record(id, versions[owner], snapshot);
    }));
    await Promise.all(authors.flatMap((sync, owner) => Array.from({ length: 20 }, (_, turn) => sync.save('draft', state(`${owner}:${turn}`)))));
    expect(versions).toEqual([20, 20, 20]); expect(confirmed.map(item => item.prompt)).toEqual(['0:19', '1:19', '2:19']);
  });
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
