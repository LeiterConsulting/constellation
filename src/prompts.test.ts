import { describe, expect, it } from 'vitest';
import { createBlank, createStarter, cleanDashboardUrl, validateDefinition } from './document';
import { contextualPrompts, promptContextKey, instanceIdeas } from './prompts';
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
    const focused = contextualPrompts(doc, 'viz_trend');
    expect(focused[0].reason).toContain(doc.visualizations.viz_trend.title);
    expect(focused[0].prompt).toContain('selected chart');
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
    expect(instanceIdeas(null)).toEqual([]);
    const ideas = instanceIdeas({ indexes: [{name:'orders',kind:'event'},{name:'_internal',kind:'event'}], status:'available', warning:'', note:'', activity:[
      {index:'_internal',sourcetype:'splunkd',events:'20000'},{index:'orders',sourcetype:'order_events',events:'100'},
    ] });
    expect(ideas[0].scope?.index).toBe('orders'); expect(ideas[0].prompt).toContain('index=orders');
    expect(ideas.every(idea => idea.prompt.includes('actual Splunk data'))).toBe(true);
    expect(JSON.stringify(ideas)).not.toMatch(/museum|fictional|customer journey/i);
    const catalogOnly = instanceIdeas({indexes:[{name:'orders',kind:'event'}],status:'available',warning:'',note:'',activity:[]});
    expect(catalogOnly[0].label).toBe('Inspect orders');
    expect(catalogOnly[0].reason).not.toContain('recent');
  });
});
