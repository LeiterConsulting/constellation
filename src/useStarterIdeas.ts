import { useEffect, useRef, useState } from 'react';
import { providerRequest } from './api';
import type { DataDiscovery, DataProfile, DataScope } from './data';
import { dataScopeKey, fieldDefinitionKey } from './data';
import { datasetQuestions, starterScopes } from './datasetQuestions';
import type { InstanceIdea } from './prompts';

type Profile = (scope: DataScope, signal: AbortSignal) => Promise<DataProfile>;
export async function inspectStarterScopes(scopes: DataScope[], cache: Map<string, DataProfile>, signal: AbortSignal,
  profile: Profile, update: (profiles: DataProfile[]) => void) {
  const profiles: DataProfile[] = [];
  for (const scope of scopes.slice(0, 3)) {
    if (signal.aborted) return;
    const key = dataScopeKey(scope) + fieldDefinitionKey(scope);
    try {
      const result = cache.get(key) || await profile(scope, signal);
      if (signal.aborted) return;
      cache.set(key, result); profiles.push(result); update([...profiles]);
    } catch { if (signal.aborted) return; /* A failed sample must not imply a dataset is empty. */ }
  }
}

export function useStarterIdeas(discovery: DataDiscovery | null, enabled: boolean, preferred?: DataScope | null) {
  const cache = useRef(new Map<string, DataProfile>());
  const checkedAt = useRef(0);
  const [ideas, setIdeas] = useState<InstanceIdea[]>([]), [loading, setLoading] = useState(false);
  const preferredKey = dataScopeKey(preferred) + fieldDefinitionKey(preferred);
  useEffect(() => {
    if (!enabled || !discovery) return;
    if (Date.now() - checkedAt.current > 300_000) { cache.current.clear(); checkedAt.current = Date.now(); }
    const controller = new AbortController(); setLoading(true);
    void inspectStarterScopes(starterScopes(discovery, preferred), cache.current, controller.signal,
      (scope, signal) => providerRequest<DataProfile>('profile', { ...scope }, signal),
      profiles => setIdeas(profiles.flatMap(profile => datasetQuestions(profile).slice(0, 1)).slice(0, 3)))
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [discovery, enabled, preferredKey]);
  return { ideas, loading };
}
