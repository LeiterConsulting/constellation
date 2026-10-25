import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import AitkSetupGuide from './AitkSetupGuide';

vi.mock('@splunk/react-ui/CollapsiblePanel', () => ({ default: ({ children, defaultOpen }: { children: React.ReactNode; defaultOpen: boolean }) => <section data-open={defaultOpen}>{children}</section> }));
vi.mock('@splunk/splunk-utils/url', () => ({ createURL: (path: string) => `/splunk/en-GB/${path}` }));

describe('AITK setup guide boundaries', () => {
  it('keeps help collapsed and native navigation under Splunk’s URL prefix', () => {
    const html = renderToStaticMarkup(<AitkSetupGuide connection="shared fixture"/>);
    expect(html).toContain('data-open="false"');
    expect(html).toContain('/splunk/en-GB/app/Splunk_ML_Toolkit/connections');
    expect(html).toContain('/splunk/en-GB/app/Splunk_ML_Toolkit/search');
    expect(html).toContain('apply_ai_commander_command');
    expect(html).toContain('representative non-admin user');
    expect(html).not.toContain('<form');
  });

  it('shows only a constant synthetic search with a validated connection name', () => {
    const valid = renderToStaticMarkup(<AitkSetupGuide connection=" shared fixture "/>);
    expect(valid).toContain('connection=&quot; shared fixture &quot;');
    for (const unsafe of ['', '   ', 'fixture" | delete', 'fixture\n| delete', '<script>fixture</script>', 'x'.repeat(201)]) {
      const html = renderToStaticMarkup(<AitkSetupGuide connection={unsafe}/>);
      expect(html).toContain('connection=&quot;your_connection&quot;');
      expect(html).not.toContain('delete');
      expect(html).not.toContain('<script>');
    }
  });
});
