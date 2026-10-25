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
      <Muted>For an administrator setting up a shared connection. Constellation keeps credentials in AITK and does not change roles or sharing automatically.</Muted>
      <Muted><strong>Shared inference:</strong> an administrator can enable an approved connection in <code>constellation_aitk.conf</code> and grant its author role only <code>constellation_use_aitk</code>. Authors do not need credential-read or AITK configuration permissions on this path. Keep the policy writable only by administrators. This opt-in handler runs only a fixed synthetic inference search; dashboard data searches still use the author’s permissions. See the administrator guide bundled with the app for setup and security review.</Muted>
      <ol>
        <li><strong>Prepare the connection.</strong> Check AITK’s <Link to="https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/install-and-upgrade-the-ai-toolkit/install-the-ai-toolkit" openInNewContext>compatible PSC version</Link> and complete any required Splunk restart. Open <Link to={createURL('app/Splunk_ML_Toolkit/connections')} openInNewContext>AI Toolkit → Connections</Link>. Create or choose an LLM connection, configure its provider credentials and model, and copy its exact name here. Check the model’s context window and Max Tokens: reasoning and visible output can share the output budget. A small successful test does not prove there is room for a full dashboard.</li>
        <li><strong>Share for use, reserve editing.</strong> In AITK, use App sharing with read access for the roles that will build dashboards. For shared inference, the connection owner must be an administrator or AITK maintainer; restrict connection writes to <code>admin</code> and <code>mltk_admin</code>. An administrator must also restrict writes on the <code>aitk_llm_connection</code> and <code>mltk_ai_commander_collection</code> KV collections to those maintainer roles. Constellation checks these permissions before inference. See the bundled administrator guide for the exact endpoints. Authors do not need “everyone” write access to use a connection.</li>
        <li><strong>Separate author and maintainer permissions.</strong> Direct/native authors need <code>apply_ai_commander_command</code> to invoke AITK; shared Constellation authors use <code>constellation_use_aitk</code> instead. <code>list_ai_commander_config</code> allows connection discovery; it does not expose tokens. Reserve <code>edit_ai_commander_config</code> for maintainers. AITK also enforces access to its stored credential; connection visibility alone does not prove inference access. <Link to="https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-commands-macros-and-visualizations/about-the-ai-command" openInNewContext>Splunk’s ai command permissions</Link></li>
        <li><strong>Test as the intended author.</strong> For shared inference, use Constellation’s Test model. For the direct/native route, sign in as a representative non-admin user. In <Link to={createURL('app/Splunk_ML_Toolkit/search')} openInNewContext>AITK Search</Link>, run this small test, which uses no indexed events:
          <pre aria-label="AITK connection test search"><code>{probe}</code></pre>
          Then return here, save the connection, run Test model, and create and edit a private dashboard using accessible data. Tests send a provider request and may incur charges. Administrator success does not prove author access.
        </li>
      </ol>
      <strong>If the test fails</strong>
      <Muted><strong>Connection unavailable:</strong> check its exact name, AITK app sharing and the author role’s read access.</Muted>
      <Muted><strong>Stored credential access denied:</strong> the direct AITK path can require <code>list_storage_passwords</code>, which can expose stored credentials. Use the administrator-managed shared inference path for ordinary authors instead of granting this capability. Keep the provider key in AITK. The native Search test above checks direct access; use Constellation’s Test model to check shared inference.</Muted>
      <Muted><strong>Empty response or model limit:</strong> check the configured model, context capacity, output allowance and provider quota. After any change, repeat the author’s test and a real dashboard flow.</Muted>
    </Guide>
  </CollapsiblePanel>;
}
