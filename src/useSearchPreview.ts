import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TokenState } from '@splunk/dashboard-types';
import { previewSummary, runPreview } from './previewJobs';
import { resultRows, searchRequest, type PreviewRows, type SearchResult } from './agent';
import type { StudioDefinition } from './document';
import { type PreviewRange } from './data';

export function useSearchPreview(definition: StudioDefinition, tokens?: TokenState, earliest: PreviewRange = '-15m') {
  const [enabled, setEnabled] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const [version, setVersion] = useState(0);
  const [status, setStatus] = useState('');
  const [running, setRunning] = useState(false);
  const [failures, setFailures] = useState<Record<string, string>>({});
  const [clock, setClock] = useState(Date.now);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 30_000); return () => window.clearInterval(timer); }, []);
  const activeRequest = useRef<AbortController | null>(null);
  const cache = useRef(new Map<string, SearchResult>());
  const run = useCallback(() => { cache.current.clear(); setEnabled(true); setEpoch(value => value + 1); setVersion(value => value + 1); }, []);
  const reset = useCallback(() => { activeRequest.current?.abort(); activeRequest.current = null; cache.current.clear(); setEnabled(false); setRunning(false); setFailures({}); setStatus(''); setVersion(value => value + 1); }, []);
  const pause = useCallback(() => { activeRequest.current?.abort(); setEnabled(false); setRunning(false); setStatus('Paused · displayed results are stale.'); }, []);
  useEffect(() => {
    if (!enabled) { setRunning(false); return; }
    const controller = new AbortController(); activeRequest.current = controller;
    const sources = Object.entries(definition.dataSources || {}).filter(([, source]) => ['ds.search', 'ds.spl2', 'ds.chain'].includes(source.type));
    setRunning(true); setFailures({});
    void (async () => {
      const completed: SearchResult[] = [];
      const problems: string[] = [];
      for (const [id] of sources.slice(0, 8)) {
        if (controller.signal.aborted) return;
        try {
          const request = searchRequest(definition, id, tokens);
          const key = JSON.stringify([request.key, earliest]);
          if (!cache.current.has(key)) {
            setStatus(`Running search ${completed.length + 1} of ${Math.min(sources.length, 8)}…`);
            const result = await runPreview(request.query, request.language, earliest, controller.signal);
            if (controller.signal.aborted) return;
            if (cache.current.size >= 32) cache.current.delete(cache.current.keys().next().value!);
            cache.current.set(key, result);
            setVersion(value => value + 1);
          }
          completed.push(cache.current.get(key)!);
        } catch (error) {
          if (controller.signal.aborted) return;
          const message = error instanceof Error ? error.message : 'The preview search failed.';
          problems.push(`${id}: ${message}`);
          setFailures(previous => ({ ...previous, [id]: message }));
        }
      }
      if (controller.signal.aborted) return;
      setRunning(false);
      setStatus(`${previewSummary(completed, problems.length) || 'No runnable searches'} · snapshot${sources.length > 8 ? ' · first 8 sources' : ''}`);
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
  const evidence = useMemo(() => Object.keys(definition.dataSources || {}).flatMap(id => {
    try {
      const request = searchRequest(definition, id, tokens);
      const cached = cache.current.get(JSON.stringify([request.key, earliest]));
      const title = Object.values(definition.visualizations).find(viz => viz.dataSources?.primary === id)?.title || id;
      if (failures[id]) return [{ id, title, state: 'failed', detail: failures[id] }];
      if (!cached) return [];
      const stale = !enabled || clock - Date.parse(cached.evidence.checkedAt) > 60_000;
      return [{ id, title, state: stale ? 'stale' : cached.state, detail: `${cached.results.length} rows · checked ${new Date(cached.evidence.checkedAt).toLocaleTimeString()}. ${cached.warning}${stale ? ' Refresh for current data.' : ''}` }];
    } catch { return []; }
  }), [definition, tokens, earliest, version, failures, enabled, clock]);
  const stale = !running && evidence.some(item => item.state === 'stale');
  const messages = useMemo(() => {
    const items: Record<string, string> = {};
    const sources = Object.entries(definition.dataSources || {}).filter(([, source]) => ['ds.search', 'ds.spl2', 'ds.chain'].includes(source.type));
    for (const [index, [id]] of sources.entries()) {
      if (results[id]) continue;
      if (index >= 8) { items[id] = 'This canvas previews the first eight search sources. Open the saved dashboard in Studio to run all sources.'; continue; }
      try { searchRequest(definition, id, tokens); } catch (error) { items[id] = error instanceof Error ? error.message : 'Choose the required input values to preview this chart.'; continue; }
      items[id] = failures[id] ? `Search preview failed. ${failures[id]}\n\nRefresh searches to retry; the saved query is preserved.`
        : enabled ? 'Search results pending.' : 'Choose Run searches to preview this chart.';
    }
    return items;
  }, [definition, tokens, results, failures, enabled]);
  return { run, pause, reset, enabled, running, results, evidence, messages, version, status: stale ? `Stale snapshots · refresh for current data.` : status };
}
