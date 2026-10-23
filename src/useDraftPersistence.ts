import { useCallback, useEffect, useRef, useState } from 'react';
import { isSplunk } from './api';
import { DraftSync, type DraftSnapshot, type DraftRecord } from './drafts';

export function useDraftPersistence(id: string, snapshot: DraftSnapshot, ready: boolean) {
  const [sync] = useState(() => new DraftSync());
  const [status, setStatus] = useState('Loading drafts…');
  const [error, setError] = useState('');
  const current = useRef({ id, snapshot }); current.current = { id, snapshot };
  const adopt = useCallback((record: DraftRecord) => { sync.adopt(record); setError(''); setStatus('Draft saved'); }, [sync]);
  const flush = useCallback(async () => {
    if (!isSplunk()) { setStatus('Local preview · drafts are not saved'); return true; }
    const captured = current.current;
    setStatus('Saving draft…');
    try {
      await sync.save(captured.id, captured.snapshot);
      if (current.current.id === captured.id) { setError(''); setStatus(sync.matches(captured.id, current.current.snapshot) ? 'Draft saved' : 'Saving draft…'); }
      return true;
    } catch (failure) {
      if (current.current.id === captured.id) { setError(failure instanceof Error ? failure.message : 'Draft could not be saved.'); setStatus('Not saved'); }
      return false;
    }
  }, [sync]);
  useEffect(() => {
    if (!ready) return;
    if (!isSplunk()) { setStatus('Local preview · drafts are not saved'); return; }
    if (sync.matches(id, snapshot)) return;
    setStatus('Saving draft…');
    const timer = window.setTimeout(() => { void flush(); }, 650);
    return () => window.clearTimeout(timer);
  }, [id, snapshot, ready, sync, flush]);
  useEffect(() => {
    const protect = (event: BeforeUnloadEvent) => {
      if (ready && isSplunk() && !sync.matches(current.current.id, current.current.snapshot)) { event.preventDefault(); event.returnValue = ''; }
    };
    window.addEventListener('beforeunload', protect);
    return () => window.removeEventListener('beforeunload', protect);
  }, [ready, sync]);
  return { adopt, flush, sync, status, error };
}
