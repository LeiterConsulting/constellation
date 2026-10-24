import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchWithDeadline } from './requestTimeout';

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
describe('bounded network waits', () => {
  it('also bounds a stalled response body after headers arrive', async () => {
    vi.useFakeTimers(); vi.stubGlobal('fetch', async () => new Response('{}'));
    const check = expect(fetchWithDeadline('https://example.test', {}, 1000, async () => new Promise(() => {}))).rejects.toThrow('Check the saved state');
    await vi.advanceTimersByTimeAsync(1000); await check; expect(vi.getTimerCount()).toBe(0);
  });
  it('releases a stalled control and explains an uncertain save outcome', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', (_url: string, init: RequestInit) => new Promise((_resolve, reject) => init.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))));
    const check = expect(fetchWithDeadline('https://example.test', { method: 'POST' }, 1000)).rejects.toThrow('Check the saved state');
    await vi.advanceTimersByTimeAsync(1000); await check;
  });
  it('preserves Stop cancellation and clears its timer after success', async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    vi.stubGlobal('fetch', (_url: string, init: RequestInit) => new Promise((_resolve, reject) => init.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))));
    const check = expect(fetchWithDeadline('https://example.test', { signal: controller.signal }, 1000)).rejects.toThrow('Aborted');
    controller.abort(); await check; expect(vi.getTimerCount()).toBe(0);
    vi.stubGlobal('fetch', async () => new Response('{}'));
    await fetchWithDeadline('https://example.test', {}, 1000); expect(vi.getTimerCount()).toBe(0);
  });
});
