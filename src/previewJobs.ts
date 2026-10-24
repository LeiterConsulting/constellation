import { providerRequest } from './api';
import type { SearchResult } from './agent';

type JobReply = SearchResult | { state: 'running'; handle?: string };
type Transport = (body: Record<string, unknown>, signal?: AbortSignal) => Promise<JobReply>;
const transport: Transport = (body, signal) => providerRequest('preview_job', body, signal);

/** Always obtain the start response, including when Stop races job creation. */
export async function runPreview(query: string, language: string, earliest: string, signal: AbortSignal, send = transport): Promise<SearchResult> {
  const started = await send({ action: 'start', query, language, earliest });
  const handle = 'handle' in started ? started.handle : undefined;
  if (!handle) throw new Error('The preview job could not be started.');
  try {
    const deadline = Date.now() + 12_000;
    while (!signal.aborted && Date.now() < deadline) {
      const result = await send({ action: 'poll', handle }, signal);
      if (signal.aborted) throw new DOMException('Preview cancelled', 'AbortError');
      if (result.state !== 'running') return { ...result, language };
      await new Promise<void>(resolve => {
        const done = () => { clearTimeout(timer); signal.removeEventListener('abort', done); resolve(); };
        const timer = setTimeout(done, 250);
        signal.addEventListener('abort', done, { once: true });
      });
    }
    if (signal.aborted) throw new DOMException('Preview cancelled', 'AbortError');
    throw new Error('The preview did not finish in time. Refresh searches to retry.');
  } finally {
    // Do not reuse the aborted signal: cancellation must reach Splunk.
    await send({ action: 'cancel', handle }).catch(() => undefined);
  }
}

export function previewSummary(results: SearchResult[], failed: number) {
  const complete = results.filter(result => result.state === 'complete').length;
  const partial = results.length - complete;
  return [complete ? `${complete} complete` : '', partial ? `${partial} partial` : '', failed ? `${failed} failed` : ''].filter(Boolean).join(' · ');
}
