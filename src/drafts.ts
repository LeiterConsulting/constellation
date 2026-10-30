import type { DashboardContextProviderProps } from '@splunk/dashboard-context';
import type { Attachment } from './agent';
import type { DataScope } from './data';
import type { StudioDefinition } from './document';
import type { PromptSuggestion } from './prompts';
import { providerRequest } from './api';
import { AppDeliveryError } from './restDelivery';

export interface ChatMessage { id: number; user: boolean; text: string; }
export interface DashboardBrief { purpose: string; requirements: string; }
export interface DraftSnapshot {
  brief?: DashboardBrief;
  definition: StudioDefinition; messages: ChatMessage[]; prompt: string; attachments: Attachment[];
  tokens?: DashboardContextProviderProps['initialTokenBinding']; activeTab?: string; selected: string;
  suggestions: PromptSuggestion[] | null; activity: string[]; saved: { name: string; url: string } | null;
  dataContext?: DataScope | null; searchesEnabled: boolean; pendingRequest?: string;
  pagePurposes?: Record<string, string>;
}
export interface DraftSummary { id: string; title: string; version: number; updatedAt: string; deletedAt: string | null; kind: 'draft' | 'native_backup'; }
export interface DraftRecord extends DraftSummary { state: DraftSnapshot;
  writeReceipt?: { id: string; baseVersion: number; version: number; digest: string };
  saveNotice?: 'recent_pointer_unavailable';
}
export interface DraftList { drafts: DraftSummary[]; trash: DraftSummary[]; activeId: string | null; owner?: string; }
export const newDraftId = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
export const openDraft = (id: string) => providerRequest<DraftRecord>('drafts', { action: 'open', id });
export const readDraft = (id: string) => providerRequest<DraftRecord>('drafts', { action: 'read', id });
export const draftSignature = (state: DraftSnapshot) => JSON.stringify(state, (_key, value) =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, value[key]])) : value);

type Writer = (id: string, version: number, state: DraftSnapshot, writeId: string) => Promise<DraftRecord>;
export interface DraftWrite { version: number; state: DraftSnapshot; writeId?: string; }
export interface DraftSaveDiagnostic { stage: string; expectedVersion: number; storedVersion?: number; writeId?: string; }
export const draftSaveDetails = (error: unknown) => {
  const detail = (error as { draftDiagnostics?: DraftSaveDiagnostic } | null)?.draftDiagnostics;
  return detail ? `${detail.stage} · expected revision ${detail.expectedVersion}${detail.storedVersion !== undefined ? ` · stored revision ${detail.storedVersion}` : ''}${detail.writeId ? ` · save ${detail.writeId}` : ''}` : '';
};
function confirmsWrite(record: DraftRecord, id: string, issued: DraftWrite) {
  return record.id === id && record.version === issued.version + 1
    && draftSignature(record.state) === draftSignature(issued.state)
    && (!record.writeReceipt || !issued.writeId || (record.writeReceipt.id === issued.writeId
      && record.writeReceipt.baseVersion === issued.version && record.writeReceipt.version === record.version));
}
/** Serializes saves per document; concurrent tabs still use server revision checks. */
export class DraftSync {
  private saved = new Map<string, { version: number; signature: string }>();
  private queues = new Map<string, Promise<DraftRecord>>();
  private writing = new Map<string, DraftWrite>();
  private previousWrite = new Map<string, DraftWrite>();
  onChange = () => {};
  constructor(private writer: Writer = (id, version, state, writeId) => providerRequest<DraftRecord>('drafts', { action: 'save', id, version, writeId, schemaVersion: 3, state }), private reader = readDraft) {}
  adopt(record: DraftRecord) { this.saved.set(record.id, { version: record.version, signature: draftSignature(record.state) }); this.previousWrite.delete(record.id); }
  resume(id: string, version: number, issued?: DraftWrite) {
    this.saved.set(id, { version, signature: '' });
    if (issued?.version === version) this.previousWrite.set(id, structuredClone(issued));
  }
  version(id: string) { return this.saved.get(id)?.version || 0; }
  issued(id: string) { return this.previousWrite.get(id) || this.writing.get(id); }
  matches(id: string, state: DraftSnapshot) { return this.saved.get(id)?.signature === draftSignature(state); }
  save(id: string, state: DraftSnapshot): Promise<DraftRecord> {
    const captured = structuredClone(state);
    const signature = draftSignature(captured);
    let uncertain = false;
    const previous = this.queues.get(id) || Promise.resolve();
    const task = previous.catch(() => undefined).then(async () => {
      let saved = this.saved.get(id);
      if (saved?.signature === signature) return { id, version: saved.version, state: captured } as DraftRecord;
      for (let attempt = 0; attempt < 2; attempt++) {
        const issuedNow = { version: saved?.version || 0, state: captured, writeId: newDraftId() };
        this.writing.set(id, issuedNow); this.onChange();
        let record: DraftRecord;
        try { record = await this.writer(id, issuedNow.version, captured, issuedNow.writeId); }
        catch (error) {
          if (error instanceof Error && !(error as Error & { draftDiagnostics?: DraftSaveDiagnostic }).draftDiagnostics) {
            (error as Error & { draftDiagnostics: DraftSaveDiagnostic }).draftDiagnostics = {
              stage: 'response', expectedVersion: issuedNow.version, writeId: issuedNow.writeId,
            };
          }
          const issued = this.previousWrite.get(id);
          if (!attempt && (error as { code?: string })?.code === 'draft_conflict' && issued?.version === (saved?.version || 0)) {
            // The old tab's save can commit after our refresh read. Rebase only on its exact receipt.
            let confirmed: DraftRecord | undefined;
            try { confirmed = await this.reader(id); } catch { /* Keep the original conflict. */ }
            if (confirmed && confirmsWrite(confirmed, id, issued)) {
              this.adopt(confirmed); saved = this.saved.get(id);
              if (saved?.signature === signature) return confirmed;
              continue;
            }
          }
          // A lost write response is not permission to write again. Confirm by readback.
          if (!(error instanceof AppDeliveryError) && (error as { code?: string })?.code !== 'draft_write_uncertain') throw error;
          uncertain = true;
          this.previousWrite.set(id, structuredClone(issuedNow));
          try {
            const confirmed = await this.reader(id);
            if (!confirmsWrite(confirmed, id, issuedNow)) throw error;
            record = confirmed;
            uncertain = false;
          } catch { throw error; }
        }
        if (record.id !== id || record.version <= issuedNow.version || draftSignature(record.state) !== signature) {
          uncertain = true; this.previousWrite.set(id, structuredClone(issuedNow));
          throw new AppDeliveryError('The saved draft response did not match this save. Your work is preserved.');
        }
        this.adopt(record); return record;
      }
      throw new Error('Draft recovery could not be confirmed. Your current work is still in this tab.');
    }).finally(() => {
      if (!uncertain) this.writing.delete(id);
      this.onChange();
    });
    this.queues.set(id, task);
    void task.finally(() => { if (this.queues.get(id) === task) this.queues.delete(id); }).catch(() => undefined);
    return task;
  }
}
