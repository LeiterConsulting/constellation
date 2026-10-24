import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import ModelReadiness from './ModelReadiness';
import type { ModelReadinessReport } from './api';

vi.mock('@splunk/react-ui/CollapsiblePanel', () => ({ default: ({ children }: { children: React.ReactNode }) => <section>{children}</section> }));
const report: ModelReadinessReport = { tested: false, warnings: ['Check the connection’s output budget.'], limits: [{ label: 'Model context', value: 'Not verified.' }], usage: {}, scope: 'This small test does not qualify full dashboard creation.' };
describe('model readiness disclosure', () => {
  it('exposes unknown limits without implying a test was run', () => {
    const html = renderToStaticMarkup(<ModelReadiness report={report}/>);
    expect(html).toContain('Not verified.'); expect(html).toContain('does not qualify full dashboard creation');
    expect(html).not.toContain('did not report token usage for this test');
  });
  it('shows reported usage only for the tested configuration, including reasoning', () => {
    const html = renderToStaticMarkup(<ModelReadiness report={{ ...report, tested: true, usage: { input_tokens: 200, output_tokens: 80, reasoning_tokens: 50 } }}/>);
    expect(html).toContain('200 input tokens'); expect(html).toContain('80 output tokens'); expect(html).toContain('50 reasoning tokens');
    const unknown = renderToStaticMarkup(<ModelReadiness report={{ ...report, tested: true }}/>);
    expect(unknown).toContain('did not report token usage');
  });
});
