export class RequestDeadlineError extends Error {}

/** Bound network waits without losing caller-driven cancellation. */
export async function fetchWithDeadline<T = Response>(url: string, init: RequestInit, milliseconds: number, consume?: (response: Response) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const external = init.signal;
  const forward = () => controller.abort(external?.reason);
  if (external?.aborted) forward(); else external?.addEventListener('abort', forward, { once: true });
  let expired = false;
  let timer: ReturnType<typeof setTimeout>;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => { expired = true; controller.abort(); reject(new Error('Request deadline')); }, milliseconds);
  });
  try {
    const operation = fetch(url, { ...init, signal: controller.signal }).then(response => consume ? consume(response) : response as T);
    return await Promise.race([operation, deadline]);
  } catch (error) {
    if (expired) throw new RequestDeadlineError('Splunk did not respond in time. Your current draft is preserved. Check the saved state before retrying.');
    throw error;
  } finally {
    clearTimeout(timer!); external?.removeEventListener('abort', forward);
  }
}
