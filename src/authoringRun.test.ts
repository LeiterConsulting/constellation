import { afterEach, describe, expect, it, vi } from 'vitest';
import { authoringRun, progressLabel } from './authoringRun';
import { providerRequest } from './api';
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; };
afterEach(() => vi.useRealTimers());
describe('authoring lifecycle', () => {
  it('releases a handle created after Stop without starting inference', async () => {
    const start = deferred<unknown>(); const controller = new AbortController();
    const request = vi.fn((action, body) => body.action === 'start' ? start.promise : Promise.resolve({}));
    const run = authoringRun({}, controller.signal, vi.fn(), request as typeof providerRequest);
    controller.abort(); start.resolve({ handle: 'fixture', events: [], stage: 'queued', seconds: 0 });
    await expect(run).rejects.toMatchObject({ name: 'AbortError' });
    expect(request.mock.calls.some(([action]) => action === 'author')).toBe(false);
    expect(request.mock.calls.some(([,body]) => body.action === 'cancel' && body.handle === 'fixture')).toBe(true);
  });
  it('polls during inference and rejects a late completion after Stop', async () => {
    vi.useFakeTimers(); const completion = deferred<unknown>(); const controller = new AbortController(); const progress = vi.fn();
    const request = vi.fn((action, body) => action === 'author' ? completion.promise : Promise.resolve(body.action === 'start' ? { handle: 'fixture', events: [], stage: 'queued', seconds: 0 } : { events: [{stage:'model',attempt:2,seconds:3}],stage:'model',seconds:3 }));
    const run = authoringRun({},controller.signal,progress,request as typeof providerRequest);
    await vi.advanceTimersByTimeAsync(500);
    expect(progress.mock.calls.at(-1)?.[0].stage).toBe('model');
    controller.abort(); const count = progress.mock.calls.length;
    completion.resolve({changes: []});
    await expect(run).rejects.toMatchObject({name:'AbortError'});
    await vi.advanceTimersByTimeAsync(5000);
    expect(progress).toHaveBeenCalledTimes(count);
    expect(request.mock.calls.some(([,body]) => body.action === 'cancel')).toBe(true);
  });
  it('does not turn a missed receipt into a failed dashboard result', async () => {
    vi.useFakeTimers();const completion=deferred<unknown>();const controller=new AbortController();
    const request=vi.fn((action,body)=>action==='author'?completion.promise:body.action==='poll'?Promise.reject(new Error('synthetic outage')):Promise.resolve({handle:'fixture',events:[],stage:'queued',seconds:0}));
    const run=authoringRun({},controller.signal,vi.fn(),request as typeof providerRequest);
    await vi.advanceTimersByTimeAsync(800); completion.resolve({changes:[],message:'Ready'});
    await expect(run).resolves.toMatchObject({message:'Ready'});
    expect(progressLabel({stage:'repair',seconds:4,events:[{stage:'repair',seconds:4,attempt:2}]})).toContain('request 2 of 3');
  });
});
