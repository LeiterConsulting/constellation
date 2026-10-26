export type PreviewRange = '-15m' | '-1h' | '-24h' | '-7d';
export interface DataScope { fieldDefinitions?: Record<string, {unit?: string; meaning?: string}>; index?: string; sourcetype?: string; query?: string; language?: 'spl' | 'spl2'; earliest: PreviewRange; }
export const fieldDefinitionKey = (scope?: DataScope | null) => JSON.stringify(Object.entries(scope?.fieldDefinitions || {}).sort(([a],[b])=>a.localeCompare(b)));
export const dataScopeKey = (scope?: DataScope | null) => scope ? JSON.stringify([scope.index || '',scope.sourcetype || '',scope.query || '',scope.language || 'spl',scope.earliest]) : '';
export interface DataDiscovery { indexes: Array<{ name: string; kind: string }>; status: string; activity: Array<{ index: string; sourcetype: string; events: string }>; warning: string; note: string; }
export interface DataProfile { scope: DataScope; baseQuery: string; fields: Array<{ name: string; numeric: boolean; present: number; coverage?: { missing: number; numeric: number; multivalue: number; basis: 'sample_rows' }; context?: { role: 'measurement' | 'identifier' | 'category' | 'counter' | 'timestamp' | 'unknown'; basis: 'platform' | 'field_name' | 'user' | 'unknown'; quantity?: string; unit?: string; meaning?: string; meaningBasis?: 'user'; nameUnitConflict?: string } }>; sampledRows: number; bounded: boolean; completion?: { state: 'complete' | 'partial' | 'unknown'; reasons: string[] }; note: string; grain?: 'existing_search_output' | 'indexed_observations'; fieldPolicy?: string; sampledRowsBasis?: 'returned_rows'; }
export const previewRanges: Array<{ value: PreviewRange; label: string }> = [
  { value: '-15m', label: 'Last 15 minutes' }, { value: '-1h', label: 'Last hour' },
  { value: '-24h', label: 'Last 24 hours' }, { value: '-7d', label: 'Last 7 days' },
];
import type { StudioDefinition } from './document';

/** A supported common native range; otherwise use an explicitly labelled bound. */
export function nativePreviewRange(definition: StudioDefinition): PreviewRange {
  const ranges = Object.values(definition.dataSources || {}).filter(source => ['ds.search', 'ds.spl2'].includes(source.type))
    .map(source => (source.options?.queryParameters as { earliest?: unknown } | undefined)?.earliest);
  return ranges.length && ranges.every(value => value === ranges[0]) && previewRanges.some(item => item.value === ranges[0]) ? ranges[0] as PreviewRange : '-15m';
}
