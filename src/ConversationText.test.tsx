import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import ConversationText from './ConversationText';

describe('conversation formatting', () => {
  it('formats model prose without permitting model-authored navigation, images or HTML', () => {
    const html = renderToStaticMarkup(<ConversationText text={'**Created** `fixture_index`\n\n![hidden](https://example.test/pixel) [Open](javascript:alert(1))\n\n<script>alert(1)</script>'}/>);
    expect(html).toContain('<strong>Created</strong>'); expect(html).toContain('fixture_index');
    expect(html).not.toContain('<img'); expect(html).not.toContain('href='); expect(html).not.toContain('<script>');
  });
});
