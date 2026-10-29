# Connect a provider

Open **Settings** in the installed Constellation workspace. Your saved provider choices remain available when you switch providers. A successful **Test model** proves a small structured response; it does not qualify every dashboard task.

## Choose a route

| Route | What you configure | Reference files |
| --- | --- | --- |
| OpenAI | Your API key and exact model ID; the official Responses endpoint is fixed. | Recognized exact models can accept images/PDFs. Unknown support is blocked. |
| Ollama | A server-reachable origin and installed model ID; native tags/show/chat APIs are used. | Images require advertised vision support. PDFs are blocked. |
| Splunk AITK | An existing named LLM connection; AITK chooses the model and keeps its credentials. | Text only. |

The [1.0 evidence](validation.md) covers direct OpenAI gpt-6-luna, Ollama qwen3-coder:latest and AITK 6.1/6.2 with OpenAI gpt-5-mini on the recorded targets. These are tested configurations, not model recommendations or a general provider success-rate claim.

## OpenAI

1. Choose **OpenAI** under **Provider**.
2. Open Splunk through trusted HTTPS and enter your key in **API key**. After saving, this becomes **Replace API key (optional)**; a saved key is not returned to the form.
3. Use **Load models** or enter an exact **Model** ID.
4. Choose **Save connection**, then **Test model**.

The key is stored encrypted with owner-restricted permissions. Ordinary authors need no credential-store capability. The adapter uses the fixed official API origin, rejects redirects and requests store:false. That request setting is not a promise of zero retention across every system.

A model appearing in inventory does not prove structured authoring or file support. If a test reports authentication, rate/quota or model-access trouble, correct the connection in Settings before retrying the dashboard request. Do not paste keys into chat, search text, an environment file or an issue.

## Ollama

1. Make the intended server/model available to the Splunk host through your normal administration process.
2. Choose **Ollama** and enter **Ollama server** as an origin, such as http://model-server:11434. Do not append an API path.
3. Use **Load models**, choose an installed ID, then **Save connection → Test model**.

Localhost means the Splunk host, not the browser's computer. Private-network HTTP is permitted; public origins require HTTPS. Embedded credentials, URL paths/queries/fragments, redirects and unsafe address categories are rejected. Constellation does not change the listener, firewall or installed models.

This route uses a configured local/server Ollama endpoint. Ollama's separate hosted API or other compatibility routes are not implied by that integration. See [Ollama's API documentation](https://docs.ollama.com/api/introduction) for the upstream interfaces.

## Splunk AITK

For ordinary authors, ask an administrator for an **approved shared connection** and the intended author role. Follow [AITK setup](aitk-setup.md) to configure that boundary; app sharing alone is insufficient.

1. Choose **Splunk AITK**.
2. Enter the exact **AITK connection name** supplied by the administrator.
3. Confirm the **Shared AITK is available** message when using the managed route.
4. Choose **Save connection → Test model**, then build and refine a small real-data dashboard.

The shared route gives authorized authors inference access without credential-store or AITK connection-management permissions. Actual data searches and draft/native storage still run as the author.

The direct/native route uses a different authority path. The tested token-backed AITK 6.1/6.2 command required credential access; invocation/list capabilities alone did not suffice. Do not grant credential-reading authority to ordinary authors as a workaround.

## Model limits

Settings reports the scope, usage and known/unknown limits of a test. Changing connection fields clears its displayed test result.

Ollama metadata can report a context capacity; the app requests at most 32,768 tokens and caps work to the available window. Direct OpenAI discovery does not provide capacity, and Constellation does not expose AITK's current upstream token/model configuration through the author route. Unknown limits remain unknown.

Compact plans and bounded staging reduce model workload while preserving final validation. They cannot overcome an insufficient output budget or inaccessible model. The qualified AITK connection used **16,000 Max Tokens / LOW reasoning effort**; an earlier 2,000-token configuration failed larger creation. Treat that as recorded evidence, not a universal minimum. AITK administrators control those settings.

If larger creation fails despite a passing test, inspect the controlled error and Activity, review capacity with the administrator, and keep the original goal. Authentication/permission failures are not repaired by rewriting the prompt.

## Reference files

| Rule | Behavior |
| --- | --- |
| Count/size | At most two files, 4 MB each. |
| Image formats | PNG, JPEG and WebP on supported routes/models. |
| PDFs | Supported recognized OpenAI models only in this integration. |
| Unknown capability | Client/server guards block transmission. |
| When sent | With the message when you choose Send. Pending files can also remain in the private draft. |

An upstream model's general capabilities are not enough: the route and exact capability evidence used by this app must permit the file. [OpenAI image input documentation](https://developers.openai.com/api/docs/guides/images-vision) describes the upstream feature; Constellation's own guard can be narrower.

## Data sent and stored

The provider can receive your prompt, recent conversation, relevant dashboard definition/SPL, selected-element context, curated guidance, field metadata and supported submitted attachments. Search-result rows are excluded from model context, but definitions, SPL literals and metadata can themselves contain sensitive information.

AITK prompt-bearing synthetic jobs follow normal Splunk history/retention behavior. Stop prevents late app edits; it cannot guarantee upstream cancellation or avoid charges. Read [security and data handling](../SECURITY.md) before using confidential material.

**Next:** [Build a dashboard](user-guide.md) · [Troubleshooting](troubleshooting.md) · [AITK administration](aitk-setup.md)
