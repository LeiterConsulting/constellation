import { describe, expect, it, vi } from 'vitest';
import { createBlank } from './document';
import { previewSourceSchedule } from './previewSources';
import { previewRequests, previewResultKey, runPreviewBatch } from './previewBatch';
import type { SearchResult } from './agent';

const result = (): SearchResult => ({ state: 'complete', fields: [{ name: 'count' }], results: [{ count: 2 }],
  language: 'spl', bounded: true, warning: '', evidence: { state: 'complete', checkedAt: new Date().toISOString(),
    earliest: '-1h', latest: 'now', resultCount: 1, finalized: false, reasons: [] } });
function board() {
  const d = createBlank();
  d.dataSources = Object.fromEntries(Array.from({ length: 32 }, (_, i) => [`s${i}`, { type: 'ds.search', options: { query: `search index=fixture group=${i} | stats count` } }]));
  d.visualizations = Object.fromEntries(Array.from({ length: 32 }, (_, i) => [`v${i}`, { type: 'splunk.table', dataSources: { primary: `s${i}` } }]));
  d.layout = { globalInputs: [], tabs: { items: Array.from({ length: 8 }, (_, i) => ({ layoutId: `p${i}` })) },
    layoutDefinitions: Object.fromEntries(Array.from({ length: 8 }, (_, i) => [`p${i}`, { type: 'absolute', structure: Array.from({ length: 4 }, (_, j) => ({ item: `v${4 * i + j}` })) }])) };
  return d;
}
const callbacks = () => ({ progress: vi.fn(), result: vi.fn(), problem: vi.fn() });
describe('active page preview scheduling', () => {
  it('reaches the final page of a 32-source board without running other pages or changing native work', () => {
    const d = board(), before = structuredClone(d);
    expect(previewSourceSchedule(d, 'p7').scheduled).toEqual(['s28', 's29', 's30', 's31']);
    expect(previewSourceSchedule(d, 'missing').scheduled).toEqual(['s0', 's1', 's2', 's3']);
    expect(d).toEqual(before);
  });
  it('prioritizes global and page inputs and includes all chart aliases, resolving chain/report ancestry without extra unconsumed jobs', () => {
    const d = board();
    d.inputs = { global: { type: 'input.dropdown', dataSources: { primary: 's20' } }, child: { type: 'input.dropdown', dataSources: { primary: 's21' } } };
    d.layout.globalInputs = ['global'];
    (d.layout.layoutDefinitions as Record<string, { structure: Array<{ item: string }> }>).p0.structure.push({ item: 'child' });
    d.dataSources!.chain = { type: 'ds.chain', options: { extend: 'report', query: '| stats count' } };
    d.dataSources!.report = { type: 'ds.savedSearch', options: { ref: 'Fixture report', app: 'search' } };
    d.visualizations.v0.dataSources = { primary: 's0', nodeSource: 'chain' };
    const schedule = previewSourceSchedule(d, 'p0');
    expect(schedule.scheduled).toEqual(['s20', 's21', 's0', 'chain', 's1', 's2', 's3']);
    const request = previewRequests(d, ['chain'])[0].request!;
    expect(Object.keys(request.sourceRequest!.sources)).toEqual(['chain', 'report']);
    expect(schedule.ids).not.toContain('report');
  });
  it('retains the eight-job page bound, supports legacy grid layouts, and never runs unplaced sources', () => {
    const d = board();
    d.layout = { type: 'grid', globalInputs: [], structure: Array.from({ length: 10 }, (_, i) => ({ item: `v${i}` })) };
    expect(previewSourceSchedule(d).scheduled).toHaveLength(8);
    expect(previewSourceSchedule(d).deferred).toEqual(['s8', 's9']);
    d.layout.structure = [];
    expect(previewSourceSchedule(d).scheduled).toEqual([]);
  });
  it('reuses fresh shared sources and ignores unrelated tokens, but refreshes stale or affected requests', async () => {
    const d = board(), cache = new Map<string, SearchResult>(), execute = vi.fn(async () => result());
    d.dataSources!.s0.options!.query = 'search index=fixture host=$host|s$ | stats count';
    const jobs = previewRequests(d, ['s0', 's1'], { default: { host: 'alpha', detail: 'one' } });
    await runPreviewBatch(jobs, cache, '-1h', new AbortController().signal, callbacks(), execute);
    const unrelated = previewRequests(d, ['s0', 's1'], { default: { host: 'alpha', detail: 'two' } });
    await runPreviewBatch(unrelated, cache, '-1h', new AbortController().signal, callbacks(), execute);
    expect(execute).toHaveBeenCalledTimes(2);
    await runPreviewBatch(previewRequests(d, ['s0', 's1'], { default: { host: 'beta' } }), cache, '-1h', new AbortController().signal, callbacks(), execute);
    expect(execute).toHaveBeenCalledTimes(3);
    cache.get(previewResultKey(jobs[1].request!, '-1h'))!.evidence.checkedAt = '2000-01-01T00:00:00Z';
    await runPreviewBatch([jobs[1]], cache, '-1h', new AbortController().signal, callbacks(), execute);
    expect(execute).toHaveBeenCalledTimes(4);
  });
  it('does not cache or publish obsolete page results and keeps waiting inputs distinct from failures', async () => {
    const d = board(), cache = new Map<string, SearchResult>(), c = new AbortController(), events = callbacks();
    await runPreviewBatch(previewRequests(d, ['s0']), cache, '-1h', c.signal, events, async () => { c.abort(); return result(); });
    expect(cache.size).toBe(0); expect(events.result).not.toHaveBeenCalled();
    d.dataSources!.s0.options!.query = 'search index=fixture host=$unset|s$';
    const summary = await runPreviewBatch(previewRequests(d, ['s0', 's1']), cache, '-1h', new AbortController().signal, events,
      async () => { throw new Error('synthetic search failure'); });
    expect(summary).toMatchObject({ waiting: 1, failed: 1 });
    expect(events.problem.mock.calls.map(call => call[2])).toEqual([true, false]);
  });
});
