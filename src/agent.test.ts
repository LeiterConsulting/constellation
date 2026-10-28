import { describe, expect, it } from 'vitest';
import { applyStudioChanges, searchRequest } from './agent';
import { createStarter } from './document';

describe('agent edits and search previews', () => {
  it('applies layout and visualization edits atomically without losing source data', () => {
    const base = { number: 4, definition: createStarter() };
    const changed = applyStudioChanges(base, { revision: 4, changes: [
      { op: 'set', path: '/title', value: '"Service Health"' },
      { op: 'set', path: '/visualizations/viz_ranked/type', value: '"splunk.column"' },
    ] });
    expect(changed.definition.dataSources).toEqual(base.definition.dataSources);
    expect(changed.definition.visualizations.viz_ranked.type).toBe('splunk.column');
    expect(base.definition.title).toBe('Checkout performance');
    expect(() => applyStudioChanges(base, { revision: 3, changes: [] })).toThrow(/changed/);
  });
  it('rejects dangerous pointer and nested properties without mutating the original', () => {
    const base = { number: 1, definition: createStarter() };
    for (const change of [
      { op: 'set' as const, path: '/visualizations/__proto__/bad', value: '"bad"' },
      { op: 'set' as const, path: '/defaults', value: '{"__proto__":{"bad":true}}' },
      { op: 'remove' as const, path: '/visualizations', value: '' },
    ]) expect(() => applyStudioChanges(base, { revision: 1, changes: [change] })).toThrow();
    expect(base.definition.title).toBe('Checkout performance');
  });
  it('resolves quoted selection tokens and preserves query language across chains', () => {
    const definition = createStarter();
    definition.dataSources!.live = { type: 'ds.spl2', options: { query: 'from main | where service=$service|s$' } };
    definition.dataSources!.chain = { type: 'ds.chain', options: { extend: 'live', query: '| stats count()' } };
    const result = searchRequest(definition, 'chain', { default: { service: 'checkout" | collect index=bad' } });
    expect(result.language).toBe('spl2');
    expect(result.query).toContain('service="checkout\\" | collect index=bad"');
    expect(() => searchRequest(definition, 'chain')).toThrow(/Choose a value/);
  });
  it('detects cycles and refuses unsafe unquoted tokens', () => {
    const definition = createStarter();
    definition.dataSources!.a = { type: 'ds.chain', options: { extend: 'a', query: '| stats count' } };
    expect(() => searchRequest(definition, 'a')).toThrow(/cycle/);
    definition.dataSources!.a = { type: 'ds.search', options: { query: 'index=$index$ | stats count' } };
    expect(() => searchRequest(definition, 'a', { default: { index: 'main | collect index=bad' } })).toThrow(/token filter/);
  });
  it('supports array append without replacing existing tabs', () => {
    const base = { number: 0, definition: createStarter() };
    const next = applyStudioChanges(base, { revision: 0, changes: [{ op: 'set', path: '/layout/tabs/items/-', value: '{"layoutId":"layout_detail","label":"Another detail"}' }] });
    expect((next.definition.layout.tabs as { items: unknown[] }).items).toHaveLength(3);
    expect((base.definition.layout.tabs as { items: unknown[] }).items).toHaveLength(2);
  });
});


describe('native token defaults and quoting',()=>{
  it('uses defaults only before a token snapshot exists, preserving absent and null unset values', () => {
    const doc = createStarter();
    doc.defaults = { tokens: { default: { choice: { value: 'A' } } } };
    doc.inputs = { choice: { type: 'input.dropdown', options: { token: 'choice', defaultValue: 'A' } } };
    doc.dataSources = { query: { type: 'ds.search', options: { query: 'search index=fixture choice=$choice|s$' } },
      report: { type: 'ds.savedSearch', options: { app: 'search', ref: 'Fixture report' } } };
    expect(searchRequest(doc, 'query').query).toContain('choice="A"');
    const snapshots: NonNullable<Parameters<typeof searchRequest>[2]>[] = [{ default: {} }, { default: { choice: null } }];
    for (const value of snapshots) {
      expect(() => searchRequest(doc, 'query', value)).toThrow(/Choose a value/);
      expect(searchRequest(doc, 'report', value).sourceRequest!.tokens).toEqual(value);
    }
    expect(searchRequest(doc, 'query', { default: { choice: 'B' } }).query).toContain('choice="B"');
  });
  it('resolves native defaults before renderer token notifications and rejects doubled quotes',()=>{
    const doc=createStarter();doc.defaults={tokens:{default:{device:{value:'*'}}}};
    doc.dataSources!.native={type:'ds.search',options:{query:'search index=main device=$device|s$'}};
    expect(searchRequest(doc,'native').query).toBe('search index=main device="*"');
    doc.dataSources!.native.options!.query='search index=main device="$device|s$"';
    expect(()=>searchRequest(doc,'native')).toThrow('already adds quotes');
  });
  it('keeps report references and chain identity for server resolution, with a complete cache key', () => {
    const doc = createStarter();
    doc.dataSources = {
      report: { type: 'ds.savedSearch', options: { ref: 'Fixture report', app: 'search' } },
      chain: { type: 'ds.chain', options: { extend: 'report', query: '| where device=$device|s$' } },
      unused: { type: 'ds.search', options: { query: 'search index=unrelated' } },
    };
    const request = searchRequest(doc, 'chain', { default: { device: 'A' } });
    expect(request.query).toBe('');
    expect(Object.keys(request.sourceRequest!.sources).sort()).toEqual(['chain', 'report']);
    expect(request.sourceRequest!.tokens.default.device).toBe('A');
    expect(request.key).not.toBe(searchRequest(doc, 'chain', { default: { device: 'B' } }).key);
    doc.dataSources.report.options!.ref = 'Another fixture report';
    expect(request.key).not.toBe(searchRequest(doc, 'chain', { default: { device: 'A' } }).key);
  });
});
