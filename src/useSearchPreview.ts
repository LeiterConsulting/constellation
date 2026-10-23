import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TokenState } from '@splunk/dashboard-types';
import { providerRequest } from './api';
import { resultRows, searchRequest, type PreviewRows, type SearchResult } from './agent';
import type { StudioDefinition } from './document';
import { previewRanges, type PreviewRange } from './data';

export function useSearchPreview(definition: StudioDefinition, tokens?: TokenState, earliest: PreviewRange = '-15m') {
  const [enabled, setEnabled] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const [version, setVersion] = useState(0);
  const [status, setStatus] = useState('');
  const [running, setRunning] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  const cache = useRef(new Map<string, SearchResult>());
  const run = useCallback(() => { cache.current.clear(); setEnabled(true); setEpoch(value => value + 1); setVersion(value => value + 1); }, []);
  const reset = useCallback(() => { activeRequest.current?.abort(); activeRequest.current = null; cache.current.clear(); setEnabled(false); setRunning(false); setStatus(''); setVersion(value => value + 1); }, []);
  const pause = useCallback(() => { activeRequest.current?.abort(); setEnabled(false); setStatus('Search previews paused. Last results remain visible until the document changes.'); }, []);
  useEffect(() => {
    if (!enabled) { setRunning(false); return; }
    const controller = new AbortController(); activeRequest.current = controller;
    const sources = Object.entries(definition.dataSources || {}).filter(([, source]) => ['ds.search', 'ds.spl2', 'ds.chain'].includes(source.type));
    setRunning(true);
    void (async () => {
      let completed = 0;
      const problems: string[] = [];
      for (const [id] of sources.slice(0, 8)) {
        if (controller.signal.aborted) return;
        try {
          const request = searchRequest(definition, id, tokens);
          const key = JSON.stringify([request.key, earliest]);
          if (!cache.current.has(key)) {
            setStatus(`Running search ${completed + 1} of ${Math.min(sources.length, 8)}…`);
            const result = await providerRequest<SearchResult>('preview', { query: request.query, language: request.language, earliest }, controller.signal);
            if (controller.signal.aborted) return;
            if (cache.current.size >= 32) cache.current.delete(cache.current.keys().next().value!);
            cache.current.set(key, result);
            setVersion(value => value + 1);
          }
          completed++;
        } catch (error) {
          if (controller.signal.aborted) return;
          problems.push(`${id}: ${error instanceof Error ? error.message : 'The preview search failed.'}`);
        }
      }
      if (controller.signal.aborted) return;
      setRunning(false);
      setStatus(`${completed} search previews ready. ${previewRanges.find(range => range.value === earliest)?.label} · at most 200 rows / 5 seconds per query. Results may be incomplete.${sources.length > 8 ? ' Only the first 8 sources run in this preview.' : ''}${problems.length ? ' ' + problems.join(' ') : ''}`);
    })();
    return () => controller.abort();
  }, [definition, tokens, enabled, epoch, earliest]);
  const results = useMemo(() => {
    const result: Record<string, PreviewRows> = {};
    for (const id of Object.keys(definition.dataSources || {})) {
      try {
        const request = searchRequest(definition, id, tokens);
        const cached = cache.current.get(JSON.stringify([request.key, earliest]));
        if (cached) result[id] = resultRows(cached);
      } catch { /* Unsupported or unresolved sources remain paused with their original definition preserved. */ }
    }
    return result;
  }, [definition, tokens, version, earliest]);
  return { run, pause, reset, enabled, running, results, version, status };
}
