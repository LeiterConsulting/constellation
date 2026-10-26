import { describe, expect, it } from 'vitest';
import { createBlank, createStarter, cleanDashboardUrl, validateDefinition } from './document';
import { contextualPrompts, nextSuggestions, promptContextKey, suggestionsDeclined } from './prompts';
import { starterScopes } from './datasetQuestions';
import { applyStudioChanges } from './agent';

describe('fresh creation and contextual prompts', () => {
  it('starts with no sample fields, charts, queries, inputs or token assumptions', () => {
    const blank = createBlank();
    expect(validateDefinition(blank)).toBe(blank);
    expect(blank.visualizations).toEqual({}); expect(blank.dataSources).toEqual({});
    expect(blank.inputs).toEqual({}); expect(blank.defaults).toEqual({});
    expect(JSON.stringify(blank)).not.toMatch(/checkout|latency|selected_service|global_time|ds_test/i);
    const another = createBlank(); blank.visualizations.unrelated = { type: 'splunk.markdown' };
    expect(another.visualizations).toEqual({});
  });
  it('can create a different domain without depending on a starter tile or source', () => {
    const blank = { number: 8, definition: createBlank() };
    const definition = applyStudioChanges(blank, { revision: 8, changes: [
      { op: 'set', path: '/title', value: '"Museum visitors"' },
      { op: 'set', path: '/visualizations/visitors', value: '{"type":"splunk.singlevalue","dataSources":{"primary":"attendance"}}' },
      { op: 'set', path: '/dataSources/attendance', value: '{"type":"ds.test","options":{"data":{"fields":[{"name":"visitors"}],"columns":[[120]]}}}' },
      { op: 'set', path: '/layout/layoutDefinitions/layout_main/structure', value: '[{"item":"visitors","type":"block","position":{"x":0,"y":0,"w":300,"h":150}}]' },
    ] }).definition;
    expect(Object.keys(definition.dataSources!)).toEqual(['attendance']);
    expect(Object.keys(definition.visualizations)).toEqual(['visitors']);
    expect(blank.definition.visualizations).toEqual({});
    expect(() => applyStudioChanges({ number: 9, definition: createBlank() }, { revision: 8, changes: [] })).toThrow(/changed/);
  });
  it('removes old dashboard deep links while preserving other URL parameters', () => {
    const url = cleanDashboardUrl('https://splunk.example/app/constellation/workspace?tab=old&form.selected_service=checkout&form.time.earliest=-24h&lang=en#main');
    expect(url).toBe('https://splunk.example/app/constellation/workspace?lang=en#main');
  });
  it('promotes a reference or the selected chart using current context', () => {
    const doc = createStarter();
    expect(contextualPrompts(doc, 'viz_trend', 1)[0].label).toBe('Build from this reference');
    doc.dataSources![String(doc.visualizations.viz_trend.dataSources?.primary)]={type:'ds.search',options:{query:'index=fixture | timechart bins=100 avg(latency) AS p95_ms'}};
    doc.visualizations.viz_trend.options!.x="> primary | seriesByName('_time')";
    const focused = contextualPrompts(doc, 'viz_trend');
    expect(focused[0].reason).toContain(doc.visualizations.viz_trend.title);
    expect(focused[0].label).toBe('Add a rolling baseline');
    expect(contextualPrompts(doc)[0].kind).toBe('data');
    expect(contextualPrompts(doc).some(prompt => prompt.kind === 'comparison')).toBe(true);
  });
  it('invalidates model proposals after edits, undo revisions, selection or tab changes', () => {
    const doc = createStarter();
    const current = promptContextKey(4, doc, '', 'layout_overview');
    expect(promptContextKey(4, doc, '')).toBe(current);
    expect(promptContextKey(5, doc, '', 'layout_overview')).not.toBe(current);
    expect(promptContextKey(4, doc, 'viz_trend', 'layout_overview')).not.toBe(current);
    expect(promptContextKey(4, doc, '', 'layout_detail')).not.toBe(current);
    expect(promptContextKey(4, doc, 'deleted_chart', 'deleted_tab')).toBe(current);
    expect(promptContextKey(4, doc, '', undefined, { index:'orders',earliest:'-24h' })).not.toBe(current);
    expect(promptContextKey(4, doc, '', undefined, { index:'orders',earliest:'-24h' })).not.toBe(promptContextKey(4, doc, '', undefined, { index:'orders',earliest:'-1h' }));
  });
  it('starts from instance-visible datasets and promotes public activity before internal logs', () => {
    const scopes = starterScopes({ indexes: [{name:'orders',kind:'event'},{name:'_internal',kind:'event'}], status:'available', warning:'', note:'', activity:[
      {index:'_internal',sourcetype:'splunkd',events:'20000'},{index:'orders',sourcetype:'order_events',events:'100'},
    ] });
    expect(scopes[0].index).toBe('orders');
    expect(starterScopes({indexes:[{name:'orders',kind:'event'}],status:'available',warning:'',note:'',activity:[]})).toEqual([]);
  });
  it('replaces generic or empty proposals with concrete next requests and honors conversation preferences', () => {
    const doc = createStarter();
    doc.dataSources![String(doc.visualizations.viz_trend.dataSources?.primary)]={type:'ds.search',options:{query:'index=fixture | timechart bins=100 avg(latency) AS p95_ms'}};
    doc.visualizations.viz_trend.options!.x="> primary | seriesByName('_time')";
    const fallback = contextualPrompts(doc, 'viz_trend');
    const weak = {label:'Refine this chart',prompt:'Make it better.',reason:'',kind:'refine' as const};
    expect(nextSuggestions([weak],fallback,{})).toEqual(fallback);
    const retry={label:'Retry your request',prompt:'Keep the original request',reason:'The prior draft is preserved.',kind:'refine' as const};
    expect(nextSuggestions([retry],fallback,{})).toEqual([retry]);
    expect(nextSuggestions([{label:'A focused request',prompt:'Do this',reason:'x'.repeat(220),kind:'refine'}],[],{})[0].reason).toHaveLength(200);
    expect(nextSuggestions([],fallback,{}).length).toBeGreaterThan(0);
    expect(nextSuggestions([],fallback,{messages:[{user:true,text:fallback[0].prompt}]})).toEqual([]);
    expect(nextSuggestions([weak],fallback,{messages:[{user:true,text:'No more suggestions, please.'}]})).toEqual([]);
    expect(suggestionsDeclined({messages:[{user:true,text:'No suggestions'},{user:true,text:'Show suggestions again'}]})).toBe(false);
    expect(suggestionsDeclined({messages:['No suggestions','Rename the chart','Use an area chart','Keep this source','Make the title clearer'].map(text=>({user:true,text}))})).toBe(true);
    const c={brief:{purpose:'Monitor the same data',requirements:'No tables'},messages:[{user:true,text:'Make it cinematic, no tables.'}]};
    expect(contextualPrompts(doc,'',0,null,{},c).some(item=>item.label.includes('row'))).toBe(false);
    expect(nextSuggestions([{label:'Add a summary table',prompt:'Add a summary table',reason:'Compare metrics.',kind:'data'}],[],c)).toEqual([]);
  });
  it('invalidates stale proposals when the conversation or standing requirements change', () => {
    const doc=createStarter(), base=promptContextKey(1,doc,'viz_trend');
    expect(promptContextKey(1,doc,'viz_trend',undefined,null,{messages:[{user:true,text:'Investigate missing readings'}]})).not.toBe(base);
    expect(promptContextKey(1,doc,'viz_trend',undefined,null,{brief:{purpose:'Monitor readings',requirements:'Keep temperatures under 150°F'}})).not.toBe(base);
    const colors=contextualPrompts(doc,'viz_trend',0,null,{}, {messages:[{user:true,text:'Change only this tile’s colors'}]});
    expect(colors[0].prompt).toContain('every other tile unchanged');
  });
  it('prioritizes missing measurement coverage and unit clarification using evidence, not numeric IDs',()=>{
    const doc=createStarter();
    const profile={scope:{index:'fixture',earliest:'-24h' as const},baseQuery:'search index=fixture',sampledRows:10,bounded:true,note:'Synthetic',fields:[
      {name:'pid',numeric:true,present:5,coverage:{missing:5,numeric:5,multivalue:0,basis:'sample_rows' as const},context:{role:'identifier' as const,basis:'field_name' as const}},
      {name:'temperature',numeric:true,present:6,coverage:{missing:4,numeric:6,multivalue:0,basis:'sample_rows' as const},context:{role:'measurement' as const,basis:'field_name' as const,quantity:'temperature'}},
    ]};
    const cards=contextualPrompts(doc,'viz_trend',0,profile.scope,{}, {profile});
    expect(cards[0].label).toBe('Show how many readings support each metric');
    expect(cards.some(card=>card.label==='Confirm temperature units')).toBe(true);
    expect(cards.some(card=>card.label.includes('pid'))).toBe(false);
    expect(cards[0].prompt).toContain('keep missing or excluded measurements null');
  });
  it('helps answer blocking questions rather than proposing unrelated edits',()=>{
    const doc=createStarter();
    const units=contextualPrompts(doc,'viz_trend',0,null,{}, {messages:[{user:false,text:'Should temperatures use Fahrenheit or Celsius?'}]});
    expect(units.map(item=>item.label)).toEqual(['Use Fahrenheit','Use Celsius']);
    expect(contextualPrompts(doc,'viz_trend',0,null,{}, {messages:[{user:false,text:'Which service should this page investigate?'}]})).toEqual([]);
  });
});
