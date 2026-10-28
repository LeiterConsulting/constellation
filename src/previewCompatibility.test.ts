import { describe, expect, it } from 'vitest';
import { nativeSupportMessage } from './previewCompatibility';

describe('native target preview compatibility', () => {
  it('keeps embedded renderer availability distinct from connected native support', () => {
    expect(nativeSupportMessage('splunk.treemap', ['splunk.table', 'splunk.timeline'])).toContain('preserved');
    expect(nativeSupportMessage('splunk.timeline', ['splunk.timeline'])).toBeNull();
    expect(nativeSupportMessage('splunk.networkGraph')).toBeNull();
  });
});
