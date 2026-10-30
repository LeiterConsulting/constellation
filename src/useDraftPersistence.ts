import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { isSplunk } from './api';
import { DraftSync, draftSaveDetails, type DraftSnapshot, type DraftRecord } from './drafts';
import { DraftRecovery } from './draftRecovery';

export function useDraftPersistence(id: string, snapshot: DraftSnapshot, ready: boolean) {
  const [sync] = useState(() => new DraftSync());
  const [status, setStatus] = useState('Loading drafts…');
  const [error, setError] = useState('');
  const [diagnostic, setDiagnostic] = useState('');
  const [recovery] = useState(() => new DraftRecovery());
  const owner = useRef('');
  const [protectedRefresh, setProtectedRefresh] = useState(true);
  const current = useRef({ id, snapshot }); current.current = { id, snapshot };
  const adopt = useCallback((record: DraftRecord, pending = false) => {
    if (pending) sync.resume(record.id, record.version); else sync.adopt(record);
    setError(''); setDiagnostic(''); setStatus(pending ? 'Saving draft…' : 'Draft saved');
  }, [sync]);
  const restore = useCallback((user: string, identifier: string, record: DraftRecord | null, deleted = false) => {
    owner.current = user;
    const restored = recovery.restore(user, identifier, record, deleted);
    if (restored?.pending) sync.resume(identifier, restored.record.version, restored.issued);
    return restored;
  }, [recovery, sync]);
  const checkpoint = useCallback(() => {
    const { id: identifier, snapshot: state } = current.current;
    if (sync.matches(identifier, state)) { recovery.clear(identifier); setProtectedRefresh(true); return true; }
    const protectedNow = recovery.checkpoint(owner.current, identifier, sync.version(identifier), state, sync.issued(identifier));
    setProtectedRefresh(protectedNow); return protectedNow;
  }, [sync, recovery]);
  useLayoutEffect(() => {
    sync.onChange = () => { if (ready && isSplunk()) checkpoint(); };
    return () => { sync.onChange = () => {}; };
  }, [sync, ready, checkpoint]);
  const flush = useCallback(async () => {
    if (!isSplunk()) { setStatus('Local preview · drafts are not saved'); return true; }
    const captured = current.current;
    checkpoint();
    setStatus('Saving draft…');
    try {
      await sync.save(captured.id, captured.snapshot);
      checkpoint();
      if (current.current.id === captured.id) { setError(''); setDiagnostic(''); setStatus(sync.matches(captured.id, current.current.snapshot) ? 'Draft saved' : 'Saving draft…'); }
      return true;
    } catch (failure) {
      if (current.current.id === captured.id) { setError(failure instanceof Error ? failure.message : 'Draft could not be saved.'); setDiagnostic(draftSaveDetails(failure)); setStatus('Not saved'); }
      return false;
    }
  }, [sync, checkpoint]);
  // Commit the recovery snapshot before the user can refresh after a visible change.
  useLayoutEffect(() => { if (ready && isSplunk()) checkpoint(); }, [id, snapshot, ready, checkpoint]);
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
      if (ready && isSplunk() && !checkpoint()) { event.preventDefault(); event.returnValue = ''; }
    };
    window.addEventListener('beforeunload', protect);
    return () => window.removeEventListener('beforeunload', protect);
  }, [ready, checkpoint]);
  return { adopt, restore, flush, sync, status: !protectedRefresh && status !== 'Draft saved' ? `${status} Keep this tab open until saved.` : status, error, diagnostic };
}
