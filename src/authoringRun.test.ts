import { afterEach, describe, expect, it, vi } from 'vitest';
import { authoringRun, progressLabel } from './authoringRun';
import { providerRequest } from './api';
import { AppDeliveryError } from './restDelivery';
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; };
afterEach(() => vi.useRealTimers());
describe('authoring lifecycle', () => {
  it('does not start an already cancelled run', async () => {
    const controller = new AbortController(); controller.abort(); const request = vi.fn();
    await expect(authoringRun({}, controller.signal, vi.fn(), request)).rejects.toMatchObject({ name: 'AbortError' });
    expect(request).not.toHaveBeenCalled();
  });
  it('keeps overlapping lost-delivery and Stop races isolated with one dispatch and one cancel each', async () => {
    vi.useFakeTimers();
    const cases = Array.from({ length: 18 }, (_, index) => {
      const controller = new AbortController(); let polls = 0;
      const reply = { revision: index, changes: [], message: `Validated ${index}` };
      const request = vi.fn((action, body) => {
        if (action === 'author') return Promise.reject(new AppDeliveryError('synthetic disconnect'));
        if (body.action === 'start') return Promise.resolve({ handle: `fixture_${index}`, events: [], stage: 'queued', seconds: 0 });
        expect(body.handle).toBe(`fixture_${index}`);
        return Promise.resolve(body.action === 'result' ? { available: polls > 1, reply } : { stage: ++polls > 1 ? 'complete' : 'model', events: [], seconds: polls });
      });
      const run = authoringRun({ revision: index }, controller.signal, vi.fn(), request as typeof providerRequest);
      const result = index % 2 ? expect(run).rejects.toMatchObject({ name: 'AbortError' }) : expect(run).resolves.toEqual(reply);
      return { controller, request, result, index };
    });
    await vi.advanceTimersByTimeAsync(500);
    cases.filter(item => item.index % 2).forEach(item => item.controller.abort());
    await vi.advanceTimersByTimeAsync(2500); await Promise.all(cases.map(item => item.result));
    for (const item of cases) {
      expect(item.request.mock.calls.filter(([action]) => action === 'author')).toHaveLength(1);
      expect(item.request.mock.calls.filter(([, body]) => body.action === 'cancel')).toHaveLength(item.index % 2 ? 1 : 0);
      expect(item.request.mock.calls.filter(([, body]) => body.action === 'ack')).toHaveLength(item.index % 2 ? 0 : 1);
    }
  });
  it('waits through early response loss until the running handler delivers, without replay', async () => {
    vi.useFakeTimers();const controller=new AbortController();const progress=vi.fn();let polls=0;
    const reply={revision:9,changes:[],message:'Validated'};
    const request=vi.fn((action,body)=>Promise.resolve(action==='author'?Promise.reject(new AppDeliveryError('Lost response')):body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:body.action==='result'?{available:polls>1,reply}:body.action==='poll'?{events:[],stage:++polls>1?'complete':'model',seconds:3}:{}));
    const run=authoringRun({},controller.signal,progress,request as typeof providerRequest);
    await vi.advanceTimersByTimeAsync(500);expect(request.mock.calls.some(([,body])=>body.action==='cancel')).toBe(false);
    expect(progress.mock.calls.at(-1)?.[0].stage).toBe('delivery');
    await vi.advanceTimersByTimeAsync(1600);await expect(run).resolves.toEqual(reply);
    expect(request.mock.calls.filter(([action])=>action==='author')).toHaveLength(1);expect(request.mock.calls.some(([,body])=>body.action==='ack')).toBe(true);
  });
  it('Stop exits while waiting for a lost response and rejects late recovered work', async () => {
    vi.useFakeTimers();const controller=new AbortController();
    const request=vi.fn((action,body)=>action==='author'?Promise.reject(new AppDeliveryError('Lost response')):Promise.resolve(body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:body.action==='poll'?{stage:'model',events:[],seconds:3}:{available:false}));
    const run=authoringRun({},controller.signal,vi.fn(),request as typeof providerRequest);const outcome=expect(run).rejects.toMatchObject({name:'AbortError'});
    await vi.advanceTimersByTimeAsync(500);controller.abort();await outcome;
    expect(request.mock.calls.filter(([action])=>action==='author')).toHaveLength(1);expect(request.mock.calls.some(([,body])=>body.action==='cancel')).toBe(true);expect(request.mock.calls.some(([,body])=>body.action==='ack')).toBe(false);
  });
  it('ends lost-delivery recovery at its existing deadline or a terminal handler state', async () => {
    for(const terminal of [false,true]){
      vi.useFakeTimers();const failure=new AppDeliveryError('Lost response');const controller=new AbortController();
      const request=vi.fn((action,body)=>action==='author'?Promise.reject(failure):Promise.resolve(body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:body.action==='poll'?{stage:terminal?'failed':'model',events:[],seconds:3}:{available:false}));
      const run=authoringRun({},controller.signal,vi.fn(),request as typeof providerRequest);const outcome=expect(run).rejects.toBe(failure);
      await vi.advanceTimersByTimeAsync(terminal?500:240001);await outcome;
      expect(request.mock.calls.filter(([action])=>action==='author')).toHaveLength(1);expect(request.mock.calls.some(([,body])=>body.action==='cancel')).toBe(true);vi.useRealTimers();
    }
  });
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
  it('recovers a completed reply when author REST delivery stalls, without replay', async () => {
    vi.useFakeTimers();const controller=new AbortController();const progress=vi.fn();
    const reply={revision:4,changes:[],message:'Validated'};
    const request=vi.fn((action,body)=>action==='author'?new Promise(()=>{}):Promise.resolve(body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:body.action==='result'?{available:true,reply}:{events:[],stage:'complete',seconds:5}));
    const run=authoringRun({revision:4},controller.signal,progress,request as typeof providerRequest);
    await vi.advanceTimersByTimeAsync(500);
    await expect(run).resolves.toEqual(reply);
    expect(request.mock.calls.filter(([action])=>action==='author')).toHaveLength(1);
    expect(request.mock.calls.some(([,body])=>body.action==='ack')).toBe(true);
    expect(request.mock.calls.some(([,body])=>body.action==='cancel')).toBe(false);
    expect(progressLabel({stage:'complete',seconds:5,events:[]})).toBe('Receiving dashboard changes');
  });
  it('discards a recovered reply arriving after Stop', async () => {
    vi.useFakeTimers();const controller=new AbortController();const result=deferred<unknown>();const completion=deferred<unknown>();
    const request=vi.fn((action,body)=>action==='author'?completion.promise:body.action==='result'?result.promise:Promise.resolve(body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:{events:[],stage:'complete',seconds:3}));
    const run=authoringRun({},controller.signal,vi.fn(),request as typeof providerRequest);
    await vi.advanceTimersByTimeAsync(500);controller.abort();result.resolve({available:true,reply:{changes:[]}});completion.resolve({changes:[]});
    await expect(run).rejects.toMatchObject({name:'AbortError'});
    expect(request.mock.calls.some(([,body])=>body.action==='ack')).toBe(false);
  });
  it('recovers an already completed reply after immediate response loss', async () => {
    const controller=new AbortController();const reply={revision:8,changes:[],message:'Validated'};
    const request=vi.fn((action,body)=>action==='author'?Promise.reject(new Error('synthetic response loss')):Promise.resolve(body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:body.action==='result'?{available:true,reply}:{}));
    await expect(authoringRun({revision:8},controller.signal,vi.fn(),request as typeof providerRequest)).resolves.toEqual(reply);
    expect(request.mock.calls.filter(([action])=>action==='author')).toHaveLength(1);
    expect(request.mock.calls.some(([,body])=>body.action==='ack')).toBe(true);
    expect(request.mock.calls.some(([,body])=>body.action==='cancel')).toBe(false);
  });
  it('retains the original failure when no completed reply exists', async () => {
    const controller=new AbortController();const failure=new Error('synthetic original failure');
    const request=vi.fn((action,body)=>action==='author'?Promise.reject(failure):Promise.resolve(body.action==='start'?{handle:'fixture',events:[],stage:'queued',seconds:0}:{available:false}));
    await expect(authoringRun({},controller.signal,vi.fn(),request as typeof providerRequest)).rejects.toBe(failure);
    expect(request.mock.calls.filter(([action])=>action==='author')).toHaveLength(1);
    expect(request.mock.calls.some(([,body])=>body.action==='cancel')).toBe(true);
  });
});
