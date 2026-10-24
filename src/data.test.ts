import { expect, it } from 'vitest';
import { createBlank } from './document';
import { nativePreviewRange } from './data';

it('uses a supported common native window without changing native source parameters', () => {
  const definition = createBlank();
  definition.dataSources = { one: { type: 'ds.search', options: { queryParameters: { earliest: '-24h', latest: 'now' } } }, two: { type: 'ds.spl2', options: { queryParameters: { earliest: '-24h' } } } };
  expect(nativePreviewRange(definition)).toBe('-24h');
  definition.dataSources.two.options!.queryParameters = { earliest: '-7d' };
  expect(nativePreviewRange(definition)).toBe('-15m');
  expect(definition.dataSources.two.options!.queryParameters).toEqual({ earliest: '-7d' });
});
