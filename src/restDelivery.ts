/** Delivery recovery never authorizes replay of inference or a write. */
import { RequestDeadlineError } from './requestTimeout';
export class AppDeliveryError extends Error {}

export async function recoverRead<T>(safe: boolean, milliseconds: number, signal: AbortSignal | undefined, operation: (remaining: number) => Promise<T>): Promise<T> {
  const deadline = Date.now() + milliseconds;
  for (let attempt = 0; ; attempt++) {
    try { return await operation(Math.max(1, deadline - Date.now())); }
    catch (error) {
      if (signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error;
      const failure = error instanceof TypeError || error instanceof RequestDeadlineError
        ? new AppDeliveryError('The Splunk connection was interrupted. Your current draft is preserved.') : error;
      if (safe && !attempt && failure instanceof AppDeliveryError && Date.now() < deadline) continue;
      throw failure;
    }
  }
}

export function retryableRead(action: string, body?: Record<string, unknown>): boolean {
  if (!body) return ['settings', 'environment', 'datasets', 'discovery', 'drafts'].includes(action);
  return ['profile', 'preview', 'dependencies'].includes(action)
    || (action === 'run' && ['poll', 'result'].includes(String(body.action)))
    || (action === 'preview_job' && body.action === 'poll')
    || (action === 'drafts' && body.action === 'read');
}
