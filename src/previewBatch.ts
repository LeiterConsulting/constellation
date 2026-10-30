import { searchRequest, type SearchResult } from './agent';
import type { StudioDefinition } from './document';
import type { TokenState } from '@splunk/dashboard-types';
import { runPreview, waitingForPreviewInput } from './previewJobs';

export function previewRequests(definition: StudioDefinition, ids: string[], tokens?: TokenState) {
  return ids.map(id => {
    try { return { id, request: searchRequest(definition, id, tokens), error: undefined }; }
    catch (error) { return { id, request: undefined, error }; }
  });
}
export const previewResultKey = (request: ReturnType<typeof searchRequest>, earliest: string) => JSON.stringify([request.key, earliest]);
export const freshPreview = (result: SearchResult, now = Date.now()) => {
  const checked = Date.parse(result.evidence.checkedAt);
  return Number.isFinite(checked) && now >= checked && now - checked < 60_000;
};

/** One bounded page batch. A cancelled/obsolete batch can neither publish a
 * result nor populate cache. The job transport retains its own cancel/finalize
 * guards, current-user authority and per-query limits.
 */
export async function runPreviewBatch(jobs: ReturnType<typeof previewRequests>, cache: Map<string, SearchResult>, earliest: string,
  signal: AbortSignal, callbacks: {
    progress: (completed: number, total: number) => void;
    result: () => void;
    problem: (id: string, message: string, waiting: boolean) => void;
  }, execute = runPreview) {
  const completed: SearchResult[] = [];
  let failed = 0, waiting = 0;
  for (const [index, job] of jobs.entries()) {
    if (signal.aborted) return;
    callbacks.progress(index + 1, jobs.length);
    try {
      if (!job.request) throw job.error;
      const key = previewResultKey(job.request, earliest);
      let result = cache.get(key);
      if (!result || !freshPreview(result)) {
        result = await execute(job.request.query, job.request.language, earliest, signal, undefined, job.request.sourceRequest);
        if (signal.aborted) return;
      }
      // Touch entries on reuse as well as execution: unused pages are evicted first.
      cache.delete(key);
      if (cache.size >= 32) cache.delete(cache.keys().next().value!);
      cache.set(key, result);
      callbacks.result();
      completed.push(result);
    } catch (error) {
      if (signal.aborted) return;
      const message = error instanceof Error ? error.message : 'The preview search failed.';
      const missingInput = waitingForPreviewInput(error);
      if (missingInput) waiting++; else failed++;
      callbacks.problem(job.id, message, missingInput);
    }
  }
  return { completed, failed, waiting };
}
