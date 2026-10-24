# Providers and multimodal references

Provider adapters share the validated Studio edit contract but retain their own endpoint, authentication and message formats. Connection success does not establish full dashboard feature parity or correctness for every selected model.

| Provider | Implemented route | Configuration | Reference files |
| --- | --- | --- | --- |
| OpenAI | Official Responses API, model inventory, structured-output requests, verified TLS and `store: false`. | API key and selected model in Settings. | Images/PDFs only for exact model IDs whose capabilities are recognized by the app. Unknown support is blocked. |
| Ollama | Native `/api/tags`, `/api/show`, `/api/chat`, JSON schema output. | A server-reachable origin and installed model. | Images only when the exact model's live metadata advertises vision. PDFs are blocked. |
| Splunk AITK | `ai` command in a current-user synthetic search under `Splunk_ML_Toolkit`. | Existing accessible named LLM connection and `apply_ai_commander_command`. | Text only; image/PDF transmission is blocked. |

OpenAI authoring, image/sketch and PDF exercises have passed on one tested Enterprise target. Ollama `qwen3-coder:latest` dashboard edits have passed on both tested target versions. AITK connection/model checks and simple dashboard edits passed through an existing OpenAI-backed connection; a fresh 0.8.0 model/JSON and title-edit check also passed in that configured environment. A second target still lacks a usable completion through its named connection. The complete new multi-page real-data journey is not yet AITK-qualified.

## Endpoint and credential boundaries

Direct OpenAI uses the fixed official origin; arbitrary OpenAI-compatible endpoints are not currently supported. The adapter rejects redirects and reports controlled errors instead of returning raw provider bodies. Splunk stores the key; it is never copied to Ollama or AITK.

Ollama origins cannot include embedded credentials, paths, queries or fragments. Private-LAN HTTP is permitted; public origins require HTTPS. Redirects and unsafe address categories such as link-local/metadata targets are rejected. The configured origin must be reachable from the Splunk host. A local browser reaching Ollama does not prove server connectivity. Constellation does not modify the Ollama listener, host firewall or model inventory.

AITK owns its provider credentials and uses its configured model. Constellation does not create AITK connections, widen roles or copy keys between providers. It sends a constant field-reference template with one synthetic prompt row, bounds polling and cancels its app-owned job when finished or timed out. Normal Splunk prompt-bearing job/history behavior still applies; consult your retention and access policies.

## What leaves the app

The model receives the request, recent conversation, relevant document/SPL, selected chart/input/page context, curated guidance and field metadata. Attachments are sent when submitted with a message through a supported route. Search-result rows are excluded from model context; that does not make queries, definitions or user-provided text non-sensitive.

OpenAI's `store: false` is a request setting, not a general promise about every provider's retention or your organization's data controls. Review the actual provider agreement and account settings before sending confidential material. See [security](../SECURITY.md).

## File guards

The app accepts at most two supported reference files, up to 4 MB each. Client and server checks cover the supported content type, signature/encoding, count/size and selected provider/model capabilities. Unknown or unsupported capabilities reject files before discovery/inference. Pending attachments can persist in a private draft and must be considered part of its sensitive content.

The repository's [napkin fixture](../tests/fixtures/README.md) is an AI-generated synthetic layout exercise, not user telemetry. The PDF generator similarly creates an authored synthetic brief. These demonstrate layout interpretation; they do not establish source-data truth or universal multimodal reliability.

## Troubleshooting

- Test the same named AITK connection as the same Splunk user in AI Toolkit before testing Constellation. Check capabilities, connection access and upstream provider availability; do not grant broad roles as a shortcut.
- For Ollama, check connectivity from the Splunk server, exact installed model ID and model metadata. A model that appears in the list may still fail the structured edit test.
- For direct OpenAI, inspect the app's controlled authentication, quota/rate, model/access or request-format error. Replace keys only through Settings over an eligible secure origin.
- A validation failure preserves the last valid dashboard. The bounded repair loop handles supported output/search errors; authentication and transport failures are not blindly retried.

Provider-specific changes belong in `provider_service.py`, `provider_adapters.py` and `model_capabilities.py`. Capability updates require tests and source verification; see [upgrade guide](upgrade-guide.md).
