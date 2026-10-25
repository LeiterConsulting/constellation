import CollapsiblePanel from '@splunk/react-ui/CollapsiblePanel';
import Link from '@splunk/react-ui/Link';
import { createURL } from '@splunk/splunk-utils/url';
import styled from 'styled-components';
import { variables as v } from '@splunk/themes';
import { Muted } from './styles';

const Guide = styled.div`
  color: ${v.contentColorDefault}; font-size: ${v.fontSizeSmall}; line-height: 1.5;
  ol { padding-left: ${v.spacingLarge}; }
  li { margin: ${v.spacingMedium} 0; }
  pre { color: ${v.contentColorDefault}; white-space: pre-wrap; overflow-wrap: anywhere; background: ${v.backgroundColorPage}; padding: ${v.spacingSmall}; }
  code { color: ${v.contentColorDefault}; background: ${v.backgroundColorPage}; }
  pre code { color: inherit; background: transparent; }
`;

export default function AitkSetupGuide({ connection }: { connection: string }) {
  // Use the same connection-name contract as the server. Never turn unvalidated
  // form text into an executable search example, even though this is display-only.
  const name = connection.trim() && /^[A-Za-z0-9_. -]{1,200}$/.test(connection) ? connection : 'your_connection';
  const probe = '| makeresults\n| eval constellation_prompt="Reply with OK."\n| ai prompt="{constellation_prompt}" connection=' + JSON.stringify(name);
  return <CollapsiblePanel title="AITK setup guide" appearance="subtle" defaultOpen={false}>
    <Guide>
      <Muted>For an administrator setting up a shared connection. Constellation keeps credentials in AITK and does not change roles or sharing.</Muted>
      <ol>
        <li><strong>Prepare the connection.</strong> Check AITK’s <Link to="https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/install-and-upgrade-the-ai-toolkit/install-the-ai-toolkit" openInNewContext>compatible PSC version</Link> and complete any required Splunk restart. Open <Link to={createURL('app/Splunk_ML_Toolkit/connections')} openInNewContext>AI Toolkit → Connections</Link>. Create or choose an LLM connection, configure its provider credentials and model, and copy its exact name here. Check the model’s context window and Max Tokens: reasoning and visible output can share the output budget. A small successful test does not prove there is room for a full dashboard.</li>
        <li><strong>Share for use, reserve editing.</strong> In AITK, use App sharing with read access for the roles that will build dashboards. Keep write access with connection maintainers. Authors do not need “everyone” write access to use a connection. Review access to the underlying provider account as well.</li>
        <li><strong>Separate author and maintainer permissions.</strong> Dashboard authors need <code>apply_ai_commander_command</code> to invoke AITK. <code>list_ai_commander_config</code> allows connection discovery; it does not expose tokens. Reserve <code>edit_ai_commander_config</code> for maintainers. AITK also enforces access to its stored credential; connection visibility alone does not prove inference access. <Link to="https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-commands-macros-and-visualizations/about-the-ai-command" openInNewContext>Splunk’s ai command permissions</Link></li>
        <li><strong>Test as the intended author.</strong> Sign in as a representative non-admin user. In <Link to={createURL('app/Splunk_ML_Toolkit/search')} openInNewContext>AITK Search</Link>, run this small test, which uses no indexed events:
          <pre aria-label="AITK connection test search"><code>{probe}</code></pre>
          Then return here, save the connection, run Test model, and create and edit a private dashboard using accessible data. Tests send a provider request and may incur charges. Administrator success does not prove author access.
        </li>
      </ol>
      <strong>If the test fails</strong>
      <Muted><strong>Connection unavailable:</strong> check its exact name, AITK app sharing and the author role’s read access.</Muted>
      <Muted><strong>Stored credential access denied:</strong> depending on the installed AITK version, token-backed connections may also require <code>list_storage_passwords</code>. This capability can expose stored credentials; it is not an inference-only permission. Do not assign it automatically. Have an administrator review credential ACLs and the installed version’s supported access model, or consult Splunk support. Keep the provider key in AITK.</Muted>
      <Muted><strong>Empty response or model limit:</strong> check the configured model, context capacity, output allowance and provider quota. After any change, repeat the author’s test and a real dashboard flow.</Muted>
    </Guide>
  </CollapsiblePanel>;
}
