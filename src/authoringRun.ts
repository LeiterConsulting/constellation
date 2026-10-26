import { providerRequest } from './api';
import type { AgentReply } from './agent';

export interface RunProgress { stage: string; seconds: number; events: { stage: string; seconds: number; attempt: number }[]; }
const labels: Record<string, string> = { queued: 'Starting', inspect: 'Checking Splunk', profile: 'Inspecting data fields', model: 'Waiting for the model', validate: 'Validating dashboard changes', search: 'Checking searches', repair: 'Correcting validation issues', complete: 'Receiving dashboard changes', failed: 'Stopped with an issue', cancelled: 'Stopped' };
export const progressLabel = (progress: RunProgress) => {
  const attempt = progress.events.at(-1)?.attempt || 0;
  return `${labels[progress.stage] || 'Working'}${attempt > 1 ? ` · request ${attempt} of 3` : ''}`;
};

/** One atomic author request, with independent short control calls. No replay. */
export async function authoringRun(body: Record<string, unknown>, signal: AbortSignal, onProgress: (value: RunProgress) => void, request = providerRequest): Promise<AgentReply> {
  let handle: string | undefined, stopped = false;
  let accepted = false;
  const transport = new AbortController();
  let deliver!: (reply: AgentReply) => void;
  const delivery = new Promise<AgentReply>(resolve => { deliver = resolve; });
  let timer: ReturnType<typeof setTimeout> | undefined;
  const cancel = () => { if (handle) void request('run', { action: 'cancel', handle }).catch(() => {}); };
  const abort = () => { stopped = true; clearTimeout(timer); transport.abort(); cancel(); };
  signal.addEventListener('abort', abort, { once: true });
  const poll = async () => {
    if (stopped || signal.aborted) return;
    try {
      const value = await request<RunProgress>('run', { action: 'poll', handle }, signal);
      if (!stopped && !signal.aborted) {
        onProgress(value);
        if (value.stage === 'complete') {
          const result = await request<{ available: boolean; reply?: AgentReply }>('run', { action: 'result', handle }, signal);
          if (result.available && result.reply && !stopped && !signal.aborted) deliver(result.reply);
        }
      }
    }
    catch { /* Do not interrupt an accepted author response for a missed receipt. */ }
    if (!stopped && !signal.aborted) timer = setTimeout(() => void poll(), 1500);
  };
  try {
    // Do not abort start: Stop racing handle creation must still release it.
    const start = await request<RunProgress & { handle: string }>('run', { action: 'start' });
    handle = start.handle;
    if (signal.aborted) { cancel(); throw new DOMException('Stopped', 'AbortError'); }
    onProgress(start);
    timer = setTimeout(() => void poll(), 400);
    const author = request<AgentReply>('author', { ...body, runHandle: handle }, transport.signal).catch(async error => {
      if (!signal.aborted) {
        try {
          const result = await request<{ available: boolean; reply?: AgentReply }>('run', { action: 'result', handle }, signal);
          if (result.available && result.reply) return result.reply;
        } catch { /* Preserve the original failure if no validated reply is available. */ }
      }
      throw error;
    });
    const reply = await Promise.race([author, delivery]);
    if (signal.aborted) throw new DOMException('Stopped', 'AbortError');
    accepted = true;
    return reply;
  } catch (error) { cancel(); throw error; }
  finally {
    stopped = true; clearTimeout(timer); transport.abort(); signal.removeEventListener('abort', abort);
    if (accepted && handle) void request('run', { action: 'ack', handle }).catch(() => {});
  }
}
