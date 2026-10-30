import { validateDefinition } from './document';
import type { DraftRecord, DraftSnapshot, DraftWrite } from './drafts';
import { draftSignature } from './drafts';

const KEY = 'constellation.pendingDraft.v1';
const MAX_CHARS = 1_500_000;
const MAX_AGE = 6 * 60 * 60 * 1000;
interface Pending { schema: 1; owner: string; id: string; version: number; time: number; state: DraftSnapshot; issued?: DraftWrite; }
type Storage = Pick<globalThis.Storage, 'getItem' | 'setItem' | 'removeItem'>;
function snapshot(state: DraftSnapshot): DraftSnapshot {
  const { definition, brief, messages, prompt, attachments, tokens, activeTab, selected, suggestions, activity, saved, dataContext, searchesEnabled, pendingRequest, pagePurposes } = state;
  return { definition, brief, messages, prompt, attachments, tokens, activeTab, selected, suggestions, activity, saved, dataContext, searchesEnabled, pendingRequest, pagePurposes };
}
/** One pending snapshot in this tab. Splunk remains authoritative; never stores connection settings. */
export class DraftRecovery {
  constructor(private storage: () => Storage = () => window.sessionStorage, private now = Date.now) {}
  private pending(owner: string): Pending | null {
    try {
      const raw = this.storage().getItem(KEY);
      if (!raw) return null;
      if (raw.length > MAX_CHARS) throw new Error();
      const value = JSON.parse(raw) as Pending;
      if (value.owner !== owner || value.schema !== 1 || !/^[a-f0-9]{32}$/.test(value.id)
        || !Number.isSafeInteger(value.version) || value.version < 0 || !Number.isFinite(value.time)
        || this.now() - value.time > MAX_AGE || value.time > this.now() + 60_000) throw new Error();
      const state = value.state;
      if (value.issued) {
        if (value.issued.version !== value.version) throw new Error();
        if (value.issued.writeId !== undefined && !/^[a-f0-9]{32}$/.test(value.issued.writeId)) throw new Error();
        validateDefinition(value.issued.state.definition);
      }
      validateDefinition(state.definition);
      if (!Array.isArray(state.messages) || state.messages.some(message => typeof message.text !== 'string' || typeof message.user !== 'boolean' || !Number.isSafeInteger(message.id))
        || !Array.isArray(state.attachments) || !Array.isArray(state.activity) || typeof state.prompt !== 'string'
        || typeof state.selected !== 'string' || (state.suggestions !== null && !Array.isArray(state.suggestions))) throw new Error();
      return value;
    } catch { this.clear(); return null; }
  }
  clear(id?: string) {
    try {
      if (!id || JSON.parse(this.storage().getItem(KEY) || 'null')?.id === id) this.storage().removeItem(KEY);
    } catch { /* Disabled browser storage cannot protect a refresh. */ }
  }
  checkpoint(owner: string, id: string, version: number, state: DraftSnapshot, issued?: DraftWrite): boolean {
    try {
      // Copy only the draft contract, never arbitrary runtime/connection properties.
      const raw = JSON.stringify({ schema: 1, owner, id, version, time: this.now(), state: snapshot(state), issued: issued ? { version: issued.version, state: snapshot(issued.state), writeId: issued.writeId } : undefined });
      if (!owner || raw.length > MAX_CHARS) throw new Error();
      this.storage().setItem(KEY, raw);
      return true;
    } catch { this.clear(id); return false; }
  }
  restore(owner: string, id: string, server: DraftRecord | null, deleted = false): { record: DraftRecord; pending: boolean; issued?: DraftWrite } | null {
    const local = this.pending(owner);
    if (!local || local.id !== id) return server ? { record: server, pending: false } : null;
    // Never resurrect a deleted/existing-but-unavailable record, or downgrade future schemas.
    if (deleted || (!server && local.version > 0)) { this.clear(id); return server ? { record: server, pending: false } : null; }
    if (server && draftSignature(server.state) === draftSignature(local.state)) { this.clear(id); return { record: server, pending: false }; }
    // Only an exact in-flight write at its expected next revision can advance our base.
    const version = server && local.issued && local.issued.version === local.version && server.version === local.version + 1
      && draftSignature(server.state) === draftSignature(local.issued.state)
      && (!server.writeReceipt || !local.issued.writeId || (server.writeReceipt.id === local.issued.writeId
        && server.writeReceipt.baseVersion === local.version && server.writeReceipt.version === server.version)) ? server.version : local.version;
    // Any other newer revision must conflict rather than overwrite another session.
    return { record: { ...(server || { id, title: local.state.definition.title || 'Untitled dashboard', updatedAt: '', deletedAt: null, kind: 'draft' }), version, state: local.state }, pending: true, issued: version === local.version ? local.issued : undefined };
  }
}
