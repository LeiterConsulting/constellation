import { describe, expect, it } from 'vitest';
import { previewSummary, runPreview, waitingForPreviewInput } from './previewJobs';
import type { SearchResult } from './agent';

const complete: SearchResult = { state: 'complete', fields: [{ name: 'count' }], results: [{ count: '5' }], language: 'spl', bounded: true, warning: '', evidence: { state: 'complete', checkedAt: '2026-10-23T00:00:00Z', earliest: '-15m', latest: 'now', resultCount: 1, finalized: false, reasons: [] } };
describe('preview job lifecycle', () => {
  it('treats missing inputs separately from transport and actual search failures', () => {
    expect(waitingForPreviewInput(Object.assign(new Error('Choose a value.'), { code: 'preview_token_unset' }))).toBe(true);
    expect(waitingForPreviewInput(Object.assign(new Error('Connection interrupted.'), { code: 'splunk_transport' }))).toBe(false);
    expect(waitingForPreviewInput(new Error('The search failed.'))).toBe(false);
  });
  it('returns completed results and releases the native job', async () => {
    const actions: unknown[] = [];
    const result = await runPreview('index=main | stats count', 'spl', '-15m', new AbortController().signal, async body => {
      actions.push(body.action);
      return body.action === 'poll' ? complete : { state: 'running', handle: 'synthetic-handle' };
    });
    expect(result).toEqual(complete); expect(actions).toEqual(['start', 'poll', 'cancel']);
  });
  it('cancels a job even when Stop races its creation', async () => {
    const controller = new AbortController(), actions: unknown[] = [];
    await expect(runPreview('query', 'spl', '-15m', controller.signal, async body => {
      actions.push(body.action); if (body.action === 'start') controller.abort();
      return { state: 'running', handle: 'synthetic-handle' };
    })).rejects.toThrow('cancelled');
    expect(actions).toEqual(['start', 'cancel']);
  });
  it('does not pass an aborted signal to cancellation or apply a late response', async () => {
    const controller = new AbortController(), actions: unknown[] = [];
    await expect(runPreview('query', 'spl', '-15m', controller.signal, async (body, signal) => {
      actions.push(body.action);
      if (body.action === 'poll') { controller.abort(); return complete; }
      if (body.action === 'cancel') expect(signal).toBeUndefined();
      return { state: 'running', handle: 'synthetic-handle' };
    })).rejects.toThrow('cancelled');
    expect(actions).toEqual(['start', 'poll', 'cancel']);
  });
  it('keeps partial evidence and failure counts distinct', () => {
    expect(previewSummary([complete, { ...complete, state: 'partial' }], 1)).toBe('1 complete · 1 partial · 1 failed');
  });
  it('starts reference previews without client-supplied report SPL and retains the replay warning', async () => {
    const sourceRequest = { id: 'report', sources: { report: { type: 'ds.savedSearch', options: { ref: 'Fixture report', app: 'search' } } }, tokens: { default: {} } };
    const result = await runPreview('', 'spl', '-1h', new AbortController().signal, async body => {
      if (body.action === 'start') {
        expect(body.sourceRequest).toEqual(sourceRequest);
        expect(body).not.toHaveProperty('query');
        return { state: 'running', handle: 'synthetic', sourceWarning: 'Current-user replay.', language: 'spl' };
      }
      return complete;
    }, sourceRequest);
    expect(result.warning).toBe('Current-user replay.');
  });
});
