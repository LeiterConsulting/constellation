import { describe, expect, it } from 'vitest';
import { previewTokenSnapshot, resetDefaults } from './previewDefaults';
import { createBlank, previewDefinition } from './document';

describe('native reset defaults', () => {
  it('supplies native null bindings for absent restored tokens without overriding current values or namespaces', () => {
    const doc = createBlank();
    doc.defaults = { tokens: { default: { choice: { value: 'A' }, retained: { value: 'original' } } } };
    const tokens = { default: { retained: 'current' }, other: { choice: 'unrelated' } };
    expect(previewTokenSnapshot(doc, tokens, { default: { input: 'default' } })).toEqual({ default: { choice: null, input: null, retained: 'current' }, other: { choice: 'unrelated' } });
    expect(tokens.default).toEqual({ retained: 'current' });
    expect(previewTokenSnapshot(doc, undefined)).toBeUndefined();
  });
  it('uses native input defaults without altering the original document', () => {
    const doc = createBlank();
    doc.defaults = { tokens: { default: { retained: { value: 'keep', future: true } } } };
    doc.inputs = { selection: { type: 'input.dropdown', options: { token: 'choice', defaultValue: 'A' } },
      text: { type: 'input.text', options: { token: 'filter', defaultValue: '*' } } };
    const before = structuredClone(doc);
    expect(resetDefaults(doc, { default: { choice: 'A', filter: '*' } })).toEqual({ tokens: { default: { retained: { value: 'keep', future: true }, choice: { value: 'A' }, filter: { value: '*' } } } });
    expect(doc).toEqual(before);
  });
  it('retains unknown and other-namespace input defaults in the preview', () => {
    const doc = createBlank();
    doc.inputs = { custom: { type: 'fixture.custom', options: { token: 'choice', defaultValue: 'keep' } },
      other: { type: 'input.text', options: { token: 'choice', tokenNamespace: 'other', defaultValue: 'keep' } } };
    expect(previewDefinition(doc, {}, { default: {} }).inputs).toEqual(doc.inputs);
  });
});
