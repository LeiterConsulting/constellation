import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TokenState } from '@splunk/dashboard-types';
import { previewSummary } from './previewJobs';
import { resultRows, searchRequest, type PreviewRows, type SearchResult } from './agent';
import type { StudioDefinition } from './document';
import { type PreviewRange } from './data';
import { previewSourceSchedule } from './previewSources';
import { previewRequests, previewResultKey, freshPreview, runPreviewBatch } from './previewBatch';

export function useSearchPreview(definition: StudioDefinition, tokens?: TokenState, earliest: PreviewRange = '-15m', activeTab?: string) {
  const [enabled, setEnabled] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const [version, setVersion] = useState(0);
  const [status, setStatus] = useState('');
  const [running, setRunning] = useState(false);
  const [failures, setFailures] = useState<Record<string, string>>({});
  const [waiting, setWaiting] = useState<Record<string, string>>({});
  const [clock, setClock] = useState(Date.now);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 30_000); return () => window.clearInterval(timer); }, []);
  const activeRequest = useRef<AbortController | null>(null);
  const cache = useRef(new Map<string, SearchResult>());
  const schedule = useMemo(() => previewSourceSchedule(definition, activeTab), [definition, activeTab]);
  const jobs = previewRequests(definition, schedule.scheduled, tokens);
  // Depend on effective requests, not the whole definition/token object: an
  // unrelated title or detail token must not restart the overview's searches.
  const workKey = JSON.stringify([schedule.page, earliest, jobs.map(job => [job.id, job.request?.key,
    job.error instanceof Error ? job.error.message : null])]);
  const run = useCallback(() => { activeRequest.current?.abort(); cache.current.clear(); setEnabled(true); setEpoch(value => value + 1); setVersion(value => value + 1); }, []);
  const reset = useCallback(() => { activeRequest.current?.abort(); activeRequest.current = null; cache.current.clear(); setEnabled(false); setRunning(false); setFailures({}); setWaiting({}); setStatus(''); setVersion(value => value + 1); }, []);
  const pause = useCallback(() => { activeRequest.current?.abort(); setEnabled(false); setRunning(false); setStatus('Paused · displayed results are stale.'); }, []);
  useEffect(() => {
    if (!enabled) { setRunning(false); return; }
    const controller = new AbortController(); activeRequest.current = controller;
    setRunning(true); setFailures({}); setWaiting({});
    void (async () => {
      const summary = await runPreviewBatch(jobs, cache.current, earliest, controller.signal, {
        progress: (index, total) => setStatus(`Running search ${index} of ${total} on this page…`),
        result: () => setVersion(value => value + 1),
        problem: (id, message, waiting) => waiting ? setWaiting(previous => ({ ...previous, [id]: message }))
          : setFailures(previous => ({ ...previous, [id]: message })),
      });
      if (!summary || controller.signal.aborted) return;
      setRunning(false);
      setStatus(`${previewSummary(summary.completed, summary.failed) || 'No completed searches'}${summary.waiting ? ` · ${summary.waiting} waiting for input` : ''} · snapshot${schedule.deferred.length ? ' · page limit reached' : ''}`);
    })();
    return () => controller.abort();
  }, [workKey, enabled, epoch]);
  const results = useMemo(() => {
    const result: Record<string, PreviewRows> = {};
    for (const id of Object.keys(definition.dataSources || {})) {
      try {
        const request = searchRequest(definition, id, tokens);
        const cached = cache.current.get(previewResultKey(request, earliest));
        if (cached) result[id] = resultRows(cached);
      } catch { /* Unsupported or unresolved sources remain paused with their original definition preserved. */ }
    }
    return result;
  }, [definition, tokens, version, earliest]);
  const evidence = useMemo(() => schedule.ids.flatMap(id => {
    try {
      const request = searchRequest(definition, id, tokens);
      const cached = cache.current.get(previewResultKey(request, earliest));
      const title = schedule.titles[id] || id;
      if (failures[id]) return [{ id, title, state: 'failed', detail: failures[id] }];
      if (waiting[id]) return [{ id, title, state: 'waiting', detail: waiting[id] }];
      if (!cached) return [];
      const stale = !enabled || !freshPreview(cached, clock);
      return [{ id, title, state: stale ? 'stale' : cached.state, detail: `${cached.results.length} rows · checked ${new Date(cached.evidence.checkedAt).toLocaleTimeString()}. ${cached.warning}${stale ? ' Refresh for current data.' : ''}` }];
    } catch { return []; }
  }), [definition, tokens, earliest, version, failures, waiting, enabled, clock, schedule]);
  const stale = !running && evidence.some(item => item.state === 'stale');
  const messages = useMemo(() => {
    const items: Record<string, string> = {};
    for (const id of schedule.ids) {
      if (results[id]) continue;
      if (schedule.deferred.includes(id)) { items[id] = 'This page exceeds the eight-source preview limit. Open the saved dashboard in Studio to run all sources.'; continue; }
      try { searchRequest(definition, id, tokens); } catch (error) { items[id] = error instanceof Error ? error.message : 'Choose the required input values to preview this chart.'; continue; }
      items[id] = waiting[id] ? `Waiting for input. ${waiting[id]}` : failures[id] ? `Search preview failed. ${failures[id]}\n\nThe saved query is preserved.`
        : enabled ? 'Search results pending.' : 'Choose Run searches to preview this chart.';
    }
    return items;
  }, [definition, tokens, results, failures, waiting, enabled, schedule]);
  return { run, pause, reset, enabled, running, results, evidence, messages, version, status: stale ? `Stale snapshots · refresh for current data.` : status };
}
