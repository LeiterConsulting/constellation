import { describe, expect, it } from 'vitest';
import { applyEdit, applyEdits, createStarter, previewDefinition, toStudioXml, validateDefinition } from './document';

describe('Studio document boundaries', () => {
  it('explains failed and native-only previews without altering saved searches', () => {
    const definition = createStarter();
    definition.dataSources!.ds_external = { type: 'ds.search', options: { query: 'index=fixture | stats count' } };
    definition.visualizations.viz_trend.dataSources = { primary: 'ds_external' };
    expect(previewDefinition(definition, {}, undefined, { ds_external: 'Search preview failed. Refresh searches to retry.' }).visualizations.viz_trend.options?.markdown).toContain('failed');
    definition.dataSources!.ds_external.type = 'ds.spl2.view';
    expect(previewDefinition(definition).visualizations.viz_trend.options?.markdown).toContain('native Studio');
    expect(definition.dataSources!.ds_external.options?.query).toBe('index=fixture | stats count');
    expect(definition.visualizations.viz_trend.type).not.toBe('splunk.markdown');
  });
  it('commits model edits atomically and rejects stale batches', () => {
    const revision = { number: 3, definition: createStarter() };
    const changed = applyEdits(revision, 3, [{ type: 'rename', title: 'Healthy' }, { type: 'compare' }]);
    expect(changed.number).toBe(4);
    expect(changed.definition.title).toBe('Healthy');
    expect(() => applyEdits(revision, 2, [{ type: 'compare' }])).toThrow(/changed/);
    expect(() => applyEdits(revision, 3, [{ type: 'rename', title: 'Wrong' }, { type: 'tile-title', id: 'missing', title: 'Bad' }])).toThrow();
    expect(revision.definition.title).toBe('Checkout performance');
  });
  it('preserves unknown Studio configuration through a targeted edit', () => {
    const definition = createStarter();
    definition.futureProperty = { retained: [1, 'two'] };
    definition.visualizations.viz_trend.futureOption = { value: 'keep' };
    const changed = applyEdit({ number: 1, definition }, 1, { type: 'rename', title: 'Changed' });
    expect(changed.definition).toEqual({ ...definition, title: 'Changed' });
    expect(definition.title).not.toBe('Changed');
  });
  it('rejects edits to a stale revision without mutating the document', () => {
    const revision = { number: 3, definition: createStarter() };
    const before = JSON.stringify(revision);
    expect(() => applyEdit(revision, 2, { type: 'rename', title: 'Wrong' })).toThrow(/changed/);
    expect(JSON.stringify(revision)).toBe(before);
  });
  it('rejects a missing data source', () => {
    const definition = createStarter();
    definition.visualizations.viz_trend.dataSources = { primary: 'missing' };
    expect(() => validateDefinition(definition)).toThrow(/missing/);
  });
  it('prevents inherited-property IDs from being treated as real tiles', () => {
    expect(() => applyEdit({ number: 0, definition: createStarter() }, 0, { type: 'tile-title', id: 'toString', title: 'Wrong' })).toThrow(/no longer/);
  });
  it('applies the sample comparison once without duplicating a field', () => {
    const first = applyEdit({ number: 0, definition: createStarter() }, 0, { type: 'compare' });
    const second = applyEdit(first, 1, { type: 'compare' });
    expect(second.definition).toEqual(first.definition);
  });
  it('pauses imported searches and external navigation only in the preview copy', () => {
    const definition = createStarter();
    definition.dataSources!.ds_external = { type: 'ds.search', options: { query: 'sensitive query' } };
    definition.visualizations.viz_trend.eventHandlers = [{ type: 'drilldown.customUrl', options: { url: 'https://example.com' } }];
    const preview = previewDefinition(definition);
    expect(preview.dataSources!.ds_external.type).toBe('ds.test');
    expect(preview.dataSources!.ds_external.options?.error).toBeUndefined();
    expect(definition.dataSources!.ds_external.type).toBe('ds.search');
    expect(preview.visualizations.viz_trend.eventHandlers).toEqual([]);
    expect(definition.visualizations.viz_trend.eventHandlers).toHaveLength(1);
  });
  it('shows a waiting panel for missing results without changing the exported chart', () => {
    const definition = createStarter();
    definition.dataSources!.ds_external = { type: 'ds.search', options: { query: 'index=main | stats count' } };
    definition.visualizations.viz_trend.dataSources = { primary: 'ds_external' };
    const preview = previewDefinition(definition);
    expect(preview.visualizations.viz_trend.type).toBe('splunk.markdown');
    expect(preview.visualizations.viz_trend.options?.markdown).toContain('pending');
    expect(definition.visualizations.viz_trend.type).not.toBe('splunk.markdown');
    const populated = previewDefinition(definition, { ds_external: { fields: [{ name: 'count' }], columns: [['5']] } });
    expect(populated.visualizations.viz_trend.type).toBe(definition.visualizations.viz_trend.type);
  });
  it('escapes XML text and safely splits CDATA terminators', () => {
    const definition = { ...createStarter(), title: '<a>&"', description: ']]>' };
    const xml = toStudioXml(definition, 'dark');
    expect(xml).toContain('theme="dark"');
    expect(xml).toContain('<label>&lt;a&gt;&amp;&quot;</label>');
    expect(xml).toContain(']]]]><![CDATA[>');
  });
  it('rejects prototype keys in imported JSON', () => {
    const definition = createStarter();
    definition.unknown = JSON.parse('{"__proto__":{"polluted":true}}');
    expect(() => validateDefinition(definition)).toThrow(/unsafe/);
  });
  it('pauses imported input navigation and external imagery while preserving the source', () => {
    const definition = createStarter();
    definition.inputs = { custom: { type: 'input.dropdown', eventHandlers: [{ type: 'drilldown.customUrl', options: { url: 'https://example.com' } }] } };
    definition.visualizations.image = { type: 'splunk.image', options: { src: 'https://example.com/image.png' } };
    const preview = previewDefinition(definition);
    expect((preview.inputs as Record<string, { eventHandlers: unknown[] }>).custom.eventHandlers).toEqual([]);
    expect(preview.visualizations.image.options).toEqual({});
    expect(definition.visualizations.image.options?.src).toBe('https://example.com/image.png');
  });
  it('retains native conditions, evaluated button tokens and range selection in preview', () => {
    const definition = createStarter();
    definition.expressions = { conditions: { show: { name: 'notes', value: "$showNotes$ = 'true'" } }, eval: { toggle: { name: 'toggle', value: "$showNotes$ = 'true' ? 'false' : 'true'" } } };
    definition.visualizations.viz_trend.containerOptions = { visibility: { showConditions: ['show'] } };
    definition.visualizations.viz_trend.eventHandlers = [{ type: 'drilldown.setTimeRange', options: { token: 'global_time', events: ['range.select'] } }];
    const preview = previewDefinition(definition);
    expect(preview.expressions).toEqual(definition.expressions);
    expect(preview.visualizations.viz_trend.containerOptions).toEqual(definition.visualizations.viz_trend.containerOptions);
    expect(preview.visualizations.viz_trend.eventHandlers).toEqual(definition.visualizations.viz_trend.eventHandlers);
  });
  it('keeps local unset-token interactions while blocking external navigation', () => {
    const definition = createStarter();
    const handlers = [
      { type: 'drilldown.unsetTokens', options: { tokenNames: ['selected_device'] } },
      { type: 'drilldown.resetTokens', options: { tokenNames: ['selected_device'] } },
      { type: 'drilldown.customUrl', options: { url: 'https://example.com' } },
    ];
    definition.visualizations.viz_trend.eventHandlers = handlers;
    const preview = previewDefinition(definition);
    expect(preview.visualizations.viz_trend.eventHandlers).toEqual(handlers.slice(0, 2));
    expect(definition.visualizations.viz_trend.eventHandlers).toHaveLength(3);
  });

});

describe('preview filter continuity',()=>{
  it('mirrors current filter values into preview defaults without changing native export defaults',()=>{
    const definition=createStarter();definition.defaults={tokens:{default:{device:{value:'*'}}}};
    const preview=previewDefinition(definition,{}, {default:{device:'Freezer Temp Monitor'}});
    expect(preview.defaults).toEqual({tokens:{default:{device:{value:'Freezer Temp Monitor'}}}});
    expect(definition.defaults).toEqual({tokens:{default:{device:{value:'*'}}}});
  });
  it('keeps an explicitly unset token unset across renderer initialization without losing reset defaults', () => {
    const definition = createStarter();
    definition.defaults = { tokens: { default: { choice: { value: 'A' } } } };
    definition.inputs = { choice: { type: 'input.dropdown', options: { token: 'choice', defaultValue: 'A', items: [{ label: 'A', value: 'A' }] } } };
    const preview = previewDefinition(definition, {}, { default: {} });
    expect(preview.defaults).toEqual({ tokens: { default: { choice: { value: null } } } });
    expect((preview.inputs as Record<string, { options: Record<string, unknown> }>).choice.options).not.toHaveProperty('defaultValue');
    expect((definition.inputs as Record<string, { options: Record<string, unknown> }>).choice.options.defaultValue).toBe('A');
  });
});
