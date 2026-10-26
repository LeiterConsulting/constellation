import { describe, expect, it } from 'vitest';
import { datasetQuestions, starterScopes } from './datasetQuestions';
import { inspectStarterScopes } from './useStarterIdeas';
import type { DataProfile, DataScope } from './data';

const profile = (fields: DataProfile['fields']): DataProfile => ({scope:{index:'fixture_events',language:'spl',earliest:'-24h'},baseQuery:'search index=fixture_events',fields,
  sampledRows:20,bounded:true,note:'Synthetic metadata',completion:{state:'partial',reasons:['sample_limit']}});
const sensor = profile([{name:'_time',numeric:true,present:20},{name:'temperature_f',numeric:true,present:8},{name:'wifi_rssi',numeric:true,present:12},{name:'device_id',numeric:false,present:20}]);
describe('field-backed starting questions',()=>{
  it('uses observed measurements, keeps sparse populations independent and assumes no thresholds',()=>{
    const questions=datasetQuestions(sensor);
    expect(questions[0].label).toBe('Track temperature and connectivity');
    expect(questions[0].reason).toContain('partial field sample');
    expect(questions[0].prompt).toContain('without discarding independent readings');
    expect(questions[0].prompt).toContain('"temperature_f"');
    expect(questions[0].prompt).not.toMatch(/150|freezer|correlated|detected/);
    expect(questions.every(item=>item.prompt.length<=1200&&item.label.length<=60&&item.reason.length<=200)).toBe(true);
    const mixed={...sensor,fields:[{name:'max_temp_c',numeric:true,present:20},...sensor.fields]};
    expect(datasetQuestions(mixed)[0].fields?.[0]).toBe('temperature_f');
  });
  it('never infers a domain from an index name or invents a time axis for aggregate output',()=>{
    const aggregate={...profile([{name:'requests',numeric:true,present:20},{name:'service',numeric:false,present:20}]),scope:{query:'search index=fixture | stats count AS requests BY service',earliest:'-24h' as const}};
    const q=datasetQuestions(aggregate);
    expect(q[0].prompt).toContain('Preserve the current search, output grain and aggregation');
    expect(q[0].prompt).not.toContain('over time');
    expect(datasetQuestions({...profile([]),scope:{index:'temperature_freezer',earliest:'-24h'}})).toEqual([]);
    expect(datasetQuestions({...sensor,sampledRows:0})).toEqual([]);
    expect(datasetQuestions(profile([{name:'_time',numeric:true,present:20},{name:'device_id',numeric:true,present:20}]))).toEqual([]);
  });
  it('offers response analysis using schema without assigning status value meanings',()=>{
    const q=datasetQuestions(profile([{name:'_time',numeric:true,present:20},{name:'response_ms',numeric:true,present:20},{name:'status',numeric:false,present:20},{name:'service',numeric:false,present:20}]));
    expect(q[0].label).toBe('Investigate response time and outcomes');
    expect(q[0].prompt).toContain('without assuming which values mean failure');
  });
  it('distinguishes IDs, censored counters and reported states from measured durations',()=>{
    const process=datasetQuestions(profile([{name:'_time',numeric:true,present:20},{name:'pid',numeric:true,present:20},{name:'process_name',numeric:false,present:20},{name:'process_state',numeric:false,present:20}]));
    expect(process[0].label).toBe('Monitor process states');
    expect(process[0].fields).not.toContain('pid');
    const ping=datasetQuestions(profile([{name:'_time',numeric:true,present:20},{name:'latency_censored_count',numeric:true,present:20},{name:'avg_latency_ms',numeric:true,present:8},{name:'packet_loss_pct',numeric:true,present:20},{name:'device',numeric:false,present:20},{name:'state',numeric:false,present:20}]));
    expect(ping[0].label).toBe('Track packet loss and device states');
    expect(ping[0].prompt).not.toContain('latency_censored_count');
  });
  it('limits background inspection to three distinct active event datasets',()=>{
    const discovery={indexes:[...['a','b','c','d'].map(name=>({name,kind:'event'})),{name:'metrics',kind:'metric'}],status:'available',warning:'',note:'',
      activity:['metrics','a','a','b','c','d'].map(index=>({index,sourcetype:'fixture',events:'20'}))};
    expect(starterScopes(discovery).map(scope=>scope.index)).toEqual(['a','b','c']);
    expect(starterScopes(discovery,{index:'d',earliest:'-1h'}).map(scope=>scope.index)).toEqual(['d','a','b']);
  });
  it('reuses session metadata and stops issuing inspections on cancellation',async()=>{
    const scopes:DataScope[]=['a','b','c','d'].map(index=>({index,earliest:'-24h'}));
    const cache=new Map<string,DataProfile>(), controller=new AbortController(),calls:string[]=[];
    await inspectStarterScopes(scopes,cache,controller.signal,async scope=>{calls.push(scope.index!);return {...sensor,scope};},()=>{});
    expect(calls).toEqual(['a','b','c']);
    let rechecked=0;
    await inspectStarterScopes(scopes,cache,controller.signal,async()=>{rechecked++;return sensor;},()=>{});
    expect(rechecked).toBe(0);
    expect(cache.size).toBe(3);
    const aborted=new AbortController();
    await inspectStarterScopes(scopes,new Map(),aborted.signal,async scope=>{aborted.abort();calls.push(scope.index!);return sensor;},()=>{throw new Error('must not publish aborted metadata');});
    expect(calls).toEqual(['a','b','c','a']);
  });
});
