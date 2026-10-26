import { describe, expect, it } from 'vitest';
import { datasetQuestions, rankedStarterQuestions, starterScopes } from './datasetQuestions';
import { inspectStarterScopes } from './useStarterIdeas';
import type { DataProfile, DataScope } from './data';

const profile = (fields: DataProfile['fields']): DataProfile => ({scope:{index:'fixture_events',language:'spl',earliest:'-24h'},baseQuery:'search index=fixture_events',fields,
  sampledRows:20,bounded:true,note:'Synthetic metadata',completion:{state:'partial',reasons:['sample_limit']}});
const sensor = profile([{name:'_time',numeric:true,present:20},{name:'temperature_f',numeric:true,present:8},{name:'wifi_rssi',numeric:true,present:12},{name:'device_id',numeric:false,present:20}]);
describe('field-backed starting questions',()=>{
  it('ranks usable measured questions ahead of generic states and unknown meanings, preserving the preferred source',()=>{
    const states={...profile([{name:'_time',numeric:true,present:20},{name:'deployment_id',numeric:false,present:20,context:{role:'identifier' as const,basis:'field_name' as const}},{name:'dataset_state',numeric:false,present:20,context:{role:'category' as const,basis:'field_name' as const}}]),scope:{index:'states',earliest:'-24h' as const}};
    const unknown={...profile([{name:'_time',numeric:true,present:20},{name:'value',numeric:true,present:20,context:{role:'unknown' as const,basis:'unknown' as const}}]),scope:{index:'values',earliest:'-24h' as const}};
    const measured={...sensor,scope:{index:'readings',earliest:'-24h' as const},fields:sensor.fields.map(field=>field.name==='temperature_f'?{...field,context:{role:'measurement' as const,basis:'field_name' as const,quantity:'temperature',unit:'°F'}}:field)};
    expect(rankedStarterQuestions([states,unknown,measured]).map(idea=>idea.scope?.index)).toEqual(['readings','states','values']);
    expect(rankedStarterQuestions([states,unknown,measured],states.scope)[0].scope?.index).toBe('states');
    expect(rankedStarterQuestions([states,unknown,measured])).toHaveLength(3);
  });
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
  it('uses provenance-labelled units and exact missing coverage without inventing a cadence',()=>{
    const p={...sensor,fields:sensor.fields.map(field=>field.name==='temperature_f'?{...field,context:{role:'measurement' as const,basis:'field_name' as const,quantity:'temperature',unit:'°F'},coverage:{missing:12,numeric:8,multivalue:0,basis:'sample_rows' as const}}:field)};
    const q=datasetQuestions(p)[0];
    expect(q.prompt).toContain('a hint, not independent verification');
    expect(q.prompt).toContain('independent valid-reading counts');
    expect(q.prompt).toContain('do not fill with zero');
    expect(q.prompt).not.toMatch(/outage|every minute|150/);
    expect(q.prompt.length).toBeLessThanOrEqual(1200);
    const unknown={...p,fields:p.fields.map(field=>field.name==='temperature_f'?{...field,context:{role:'measurement' as const,basis:'field_name' as const,quantity:'temperature'}}:field)};
    expect(datasetQuestions(unknown)[0].prompt).toContain('Confirm the recorded units');
  });
  it('asks for undefined numeric meanings and uses explicitly supplied quantity context',()=>{
    const unknown=profile([{name:'_time',numeric:true,present:20},{name:'dataset_size_disclosed',numeric:true,present:20,context:{role:'unknown',basis:'unknown'}}]);
    const q=datasetQuestions(unknown)[0];expect(q.label).toBe('Clarify dataset size disclosed');expect(q.prompt).toContain('do not average an undefined numeric field');
    const defined=profile([{name:'_time',numeric:true,present:20},{name:'value',numeric:true,present:20,context:{role:'measurement',basis:'user',quantity:'duration',unit:'ms'}}]);
    expect(datasetQuestions(defined)[0].label).toBe('Investigate slow responses');
    const aggregate=profile([{name:'count',numeric:true,present:20,context:{role:'counter',basis:'field_name'}}]);
    expect(datasetQuestions(aggregate)[0].label).toBe('Visualize count');expect(datasetQuestions(aggregate)[0].prompt).toContain('Preserve the current search, output grain');
  });
  it('limits background inspection to three distinct active event datasets',()=>{
    const discovery={indexes:[...['a','b','c','d'].map(name=>({name,kind:'event'})),{name:'metrics',kind:'metric'}],status:'available',warning:'',note:'',
      activity:['metrics','a','a','b','c','d'].map(index=>({index,sourcetype:'fixture',events:'20'}))};
    expect(starterScopes(discovery).map(scope=>scope.index)).toEqual(['a','b','c']);
    expect(starterScopes(discovery,{index:'d',earliest:'-1h'}).map(scope=>scope.index)).toEqual(['d','a','b']);
  });
  it('prefers response measurements over generic durations and counter evidence',()=>{
    const p=profile([{name:'_time',numeric:true,present:20},
      {name:'duration_ms',numeric:true,present:20,context:{role:'measurement',basis:'field_name',quantity:'duration',unit:'ms'}},
      {name:'counter_evidence_level',numeric:false,present:20,context:{role:'counter',basis:'field_name'}},
      {name:'response_time_ms',numeric:true,present:20,context:{role:'measurement',basis:'field_name',quantity:'duration',unit:'ms'}}]);
    const q=datasetQuestions(p)[0];
    expect(q.label).toBe('Investigate slow responses');
    expect(q.fields).toContain('response_time_ms');
    expect(q.fields).not.toContain('duration_ms');expect(q.fields).not.toContain('counter_evidence_level');
  });
  it('keeps different scoped definitions out of the same metadata cache entry',async()=>{
    const cache=new Map<string,DataProfile>(), signal=new AbortController().signal;
    let calls=0;
    for(const unit of ['ms','s']) await inspectStarterScopes([{index:'fixture',earliest:'-24h',fieldDefinitions:{latency:{unit}}}],cache,signal,async scope=>{calls++;return {...sensor,scope};},()=>{});
    expect(calls).toBe(2);expect(cache.size).toBe(2);
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
