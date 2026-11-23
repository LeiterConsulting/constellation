# Constellation dashboard creation over Splunk MCP

Preview contract v1 · Constellation 1.1.0-preview

An explicit request to create a dashboard from a Discovery conversation or report produces a private Dashboard Studio view and a private editable Constellation draft. Discovery displays **Open dashboard** and **Edit in Constellation** from the returned receipt. A dashboard opened in Studio is an independent copy. To publish later draft edits, the author uses **Save to Splunk** to create another copy. [Splunk Discovery Tool repository](https://github.com/LeiterConsulting/splunk-discovery-tool)

## Tools

| App stanza name | MCP callable name | Arguments | Effect |
| --- | --- | --- | --- |
| `create_dashboard` | `constellation_create_dashboard` | `schema_version`, `request_id`, `expected_user`, `brief_json` | Create one new draft and one new private native view for the authenticated author. |
| `get_creation_status` | `constellation_get_creation_status` | `schema_version`, `request_id`, `expected_user` | Read the author's creation receipt and recover links after a lost response. |
| `inspect_dashboard_source` | `constellation_inspect_dashboard_source` | `schema_version`, `expected_user`, `scope_json` | Optional field and sample coverage for the selected source under the authenticated caller. |

The registration app ID is `constellation`. Qualify the exact names and schemas returned by `tools/list` on each supported server version. Discovery binds the two approved names to a configured instance and verifies their argument schemas. The application contract below is inside the MCP result envelope. The envelope mapping is part of the server qualification.

Create and Status accept `schema_version: "1"` and the same caller-generated `request_id`. The client generates the ID before dispatch using a UTC timestamp and 32 lowercase hex characters from a random UUID, for example `20261120T150000Z-1ebac9f4b9284a50aee98820181a5e61`. It records the ID with the initiating turn and the current connection binding. The JSON-RPC message ID serves transport correlation only. The client supplies `expected_user` from its verified connection binding. The server compares this assertion to the authenticated Splunk session before any work. Only the session supplies authority. A mismatch returns `identity_unavailable` and reveals no operation details.

## Optional source inspection

`constellation_inspect_dashboard_source` accepts three required scalar strings. Set `schema_version` to `"1"`, derive `expected_user` from the same verified connection used for Create and serialize one object with exactly `source` and `time_range` as `scope_json`. Use the literal index or guarded SPL forms below. The same rolling windows apply. The initial endpoint works in pilot authoring mode for its allowlisted users. POST keeps the query out of the request URL. The endpoint runs one bounded search job as the caller.

```json
{
  "schema_version": "1",
  "expected_user": "example_author",
  "scope_json": "{\"source\":{\"kind\":\"index\",\"index\":\"example_metrics\",\"sourcetype\":\"example:service\"},\"time_range\":{\"earliest\":\"-24h\",\"latest\":\"now\"}}"
}
```

Example application payload

```json
{
  "schema_version": "1",
  "status": "observed",
  "source": {"kind": "index", "index": "example_metrics", "sourcetype": "example:service", "language": "spl"},
  "time_range": {"earliest": "-24h", "latest": "now"},
  "sample": {
    "rows": 18, "row_limit": 200, "grain": "indexed_observations",
    "completion": "partial", "reasons": ["resource_limit"]
  },
  "fields": [
    {"name": "latency_ms", "present": 15, "missing": 3, "numeric": 15, "multivalue": 0,
     "role": "measurement", "unit": "ms", "basis": "field_name"}
  ]
}
```

- `observed` means the sample contains output rows, including partial samples. `empty` requires a complete zero-row sample. An incomplete zero-row sample or a preview deadline returns `inconclusive`.
- Completion is `complete`, `partial` or `unknown`. Reason codes are `resource_limit`, `row_limit`, `unverified_completion`, `search_warning`, `byte_limit`, `preview_timeout` and `dynamic_field_names`. The last reason marks a field list suppressed because a query can derive output-column names from values. It describes the field list independently of search completion.
- For SPL, `source` contains `kind` and `language`, and sample grain is `existing_search_output`. Aggregate output rows can exist when the underlying event count is zero. Coverage counts use retained rows. The shortlist contains up to 12 fields. Unit hints are optional and labelled by provenance. Render field names as text.
- The response excludes the original SPL, event values, native search handles, diagnostics and secrets. Inspection uses no inference provider, draft, dashboard or creation receipt. The existing five-second native search limit and polling limits apply. Discovery should keep the card responsive while a sample runs.
- A failed call can return a bounded error code such as `invalid_request`, `unsupported_contract`, `identity_unavailable`, `feature_disabled`, `pilot_probe_only`, `inspection_failed` or `inspection_unavailable`. Handle the MCP transport envelope first. Capability absence, an unavailable sample or discarded stale data should leave Create available under its usual rules.

Bind advisory evidence to the verified connection, Splunk user, exact selected source and range, and discard late results when the binding changes. Discovery supplies the reviewed source and time range in Create. Constellation runs fresh source, provider, search, Studio and private-write checks. Inspection results grant no authority and are outside the Create and Status schemas.

## Creation arguments

The gateway uses scalar strings. Discovery constructs and validates the inner object and serializes it exactly once into `brief_json`. Constellation independently checks both layers, rejects unknown keys and duplicate JSON keys, and enforces a 16 KiB UTF-8 brief limit. Verify scalar mapping, quotes, backslashes, Unicode and literal dollar signs through the installed registration.

| Brief field | Contract |
| --- | --- |
| `title` | Required, 1–120 characters. Display title only. |
| `purpose` | Required, 1–500 characters. State the question and intended audience. |
| `requirements` | Optional, up to 1,200 characters. Units, metric definitions, exclusions and missing-data rules. |
| `source` | Required, exactly one of the tagged forms below. |
| `time_range` | Required rolling window. `earliest` is one of `-15m`, `-1h`, `-24h`, `-7d`. `latest` is `now`. Ask about the intended period if the source finding is historical and a rolling range would change the question. |
| `pages` | Required, one or two ordered pages with unique names. Each has `name` (1–60 characters) and one to four `panels` (each 1–240 characters describing intent). At most six panels across the request. |
| `findings` | Optional, up to four concise statements (each 1–300 characters) selected from the current authorized conversation or report. Findings guide authoring. Splunk searches establish what can be rendered as a live metric. |
| `provenance` | Optional `{"kind":"conversation" or "discovery_report","label":"..."}`. Label up to 120 characters, chosen for the user. It grants no authority. |

Source forms:

- `{"kind":"index","index":"example_metrics","sourcetype":"example:service"}`. The sourcetype is optional. Constellation checks the literal scope under the caller.
- `{"kind":"spl","query":"search index=example_metrics sourcetype=example:service"}`. Up to 8,000 characters and subject to the existing guarded search and namespace rules. Prefer a verified base search in the Constellation app namespace.
- `{"kind":"saved_report","app":"search","name":"Example service observations"}`. Use the exact app and report name. Constellation resolves it as the caller in the original app. This form ships only after caller-scoped preview and native report execution behavior are verified on the target version.

The pilot accepts one SPL scope, private output in the Constellation app and a small board. Client inputs carry intent and approved source references. Constellation derives the caller, IDs, permissions, URLs and provider from its own runtime and configuration. Unsupported dependencies or time semantics produce a clarification or failure. Report findings with no qualifying live source remain findings.

Synthetic `tools/call` arguments, shown with the proposed callable name:

```json
{
  "name": "constellation_create_dashboard",
  "arguments": {
    "schema_version": "1",
    "expected_user": "example_author",
    "request_id": "20261120T150000Z-1ebac9f4b9284a50aee98820181a5e61",
    "brief_json": "{\"title\":\"Service observations\",\"purpose\":\"Help operators review arrivals and coverage.\",\"requirements\":\"Show observation counts. Leave missing measurements unknown.\",\"source\":{\"kind\":\"index\",\"index\":\"example_metrics\",\"sourcetype\":\"example:service\"},\"time_range\":{\"earliest\":\"-24h\",\"latest\":\"now\"},\"pages\":[{\"name\":\"Overview\",\"panels\":[\"Event arrivals over time\",\"Observation count by service\"]}],\"provenance\":{\"kind\":\"discovery_report\",\"label\":\"Service coverage review\"}}"
  }
}
```

## Receipt

Every application receipt carries string `schema_version`, `request_id`, `status` and an array of `warnings` with bounded `code` and `message`. `message` is optional display text. `running` also carries `stage` (`accepted`, `authoring`, `validating`, `saving_draft` or `saving_native`) and `poll_after_ms`. `needs_input` carries one `question` and may carry a safe `code`. `failed` and `indeterminate` carry a safe `code`. Treat unknown statuses or versions as a client compatibility error.

| Status | What Discovery shows | Links |
| --- | --- | --- |
| `running` | Creating dashboard, with the current stage. Poll using the same ID and connection. | None. |
| `created` | Dashboard created. Include any validation warnings. | Both verified links on creation. A later lookup omits any link and ID whose object is inaccessible or missing and adds a warning. |
| `draft_only` | Draft saved. Open it in Constellation to review and save a native copy. | Edit link if the draft remains accessible. |
| `needs_input` | Ask the returned question. Submit the revised brief with a new ID after the user answers. | None. |
| `failed` | Show safe failure guidance. A new attempt requires user intent. | None. |
| `indeterminate` | Creation could not yet be confirmed. Leave the request available for a later status check. | Only an independently confirmed private draft may have an edit link. |
| `not_found` | No usable receipt for this connection and caller. | None. Status tool only. |

For status lookup, send the same `schema_version`, `expected_user` and `request_id` without the brief.

An authoring-mode `not_found` response may include `pilot.receipt_capacity` for the verified caller. Its `limit`, `retained` and `available` counts describe that caller's seven-day receipt window. `next_expiration` is the next retained receipt's expiration in UTC or null for an empty window. This lookup does not reserve capacity. It excludes the separate pilot-wide limit and one-active-request check. A Create refused with `pilot_capacity` was never admitted and has no receipt.

### Actionable authoring reasons

Constellation stores the reason with the terminal receipt. Status returns the same code and question as Create for that request. Earlier receipts and general clarifications may include only the question. Display the question when a client lacks a specific action for its code.

| Status | Code | When to use it |
| --- | --- | --- |
| `needs_input` | `source_unavailable` | The selected source was unsupported or could not be inspected under the caller. An inconclusive sample belongs here. Review access, scope or time range. |
| `needs_input` | `no_data` | A complete bounded sample returned zero rows. Try a different source or time range. The fixed fixture also uses `no_data` as a failure code. |
| `needs_input` | `panel_coverage` | The proposed dashboard did not satisfy the approved page and panel plan or lacked usable search receipts. Simplify the selected panels. |
| `needs_input` | `authoring_settings` | The caller has no completed provider configuration or its route or model differs from the approved configuration. Review Constellation Settings. |
| `failed` | `provider_timeout`, `provider_connection` | The provider timed out or its connection was unavailable. Check the connection before retrying. |
| `failed` | `model_token_limit`, `model_output_limit` | The input exceeded the model's context budget or the output reached its limit. Try a narrower plan or a suitable model. |
| `failed` | `recovery_budget` | Authoring reached an explicit search, inference or recovery budget. Simplify the plan before retrying. |
| `failed` | `validation_failed` | A check failed without one of the typed reasons above. |

Questions use fixed text. The receipt contains no provider response body, validation trace or search text. Once saving starts, ambiguous writes still use `indeterminate` and `write_unconfirmed` or reconcile by exact readback.

Example success receipt

```json
{
  "schema_version": "1",
  "request_id": "20261120T150000Z-1ebac9f4b9284a50aee98820181a5e61",
  "status": "created",
  "title": "Service observations",
  "draft_id": "8f73c2a15c0e4d8db6a7f21c9e6430ab",
  "dashboard_id": "constellation_0cb91a8ef23d4c6075e196aa",
  "view_url": "https://splunk.example.com/en-US/app/constellation/constellation_0cb91a8ef23d4c6075e196aa",
  "edit_url": "https://splunk.example.com/en-US/app/constellation/workspace?draft=8f73c2a15c0e4d8db6a7f21c9e6430ab",
  "validation": {
    "draft_readback": "verified",
    "native_readback": "verified",
    "owner_and_privacy": "verified",
    "search_checks": "bounded"
  },
  "warnings": []
}
```

Only verified resources get IDs and links. A receipt describes what was verified at creation. Later lookup checks current authorization and existence for any returned link. It allows legitimate edits since creation. Links use a deployment-configured HTTPS Splunk Web base, including locale and any proxy prefix, and have no embedded credentials. Splunk Web requires the owning user's normal login.

## Delivery and privacy

- Within one instance and authenticated principal, the first accepted request binds its ID to a digest of the parsed, validated brief. Object-key ordering and JSON whitespace do not affect the digest. Page and panel order is significant. The same ID and brief return the existing operation. A different brief returns `request_conflict`.
- Proposed pilot retention is seven days for the private receipt. Admit new IDs for 24 hours from their embedded UTC timestamp with up to five minutes of future clock skew. An expired ID can retrieve a retained receipt and cannot start creation. Bound concurrency and storage independently of the existing per-turn search limits.
- On lost delivery, status first. The client may repeat the identical request once with the same ID only after a valid `not_found` on the same verified binding while the ID is fresh. Never mint a replacement ID automatically. An ambiguous result remains visible for reconciliation.
- MCP or transport errors are handled before interpreting the receipt. A JSON-RPC error, `isError`, invalid wrapper or unknown status never renders a successful artifact. Define safe domain error mappings such as `request_conflict`, `unsupported_contract`, `feature_disabled` and `identity_unavailable` in transport qualification.
- Discovery checks the user's explicit request, report access, per-user connection and outbound AI policy before dispatch. The pilot blocks creation when Incognito is active because Constellation performs separate inference. Status for an existing request may run as a read-only action without sending receipt contents to a model.
- Constellation receives the minimized brief and enforces the pilot’s outbound provider policy against the actual selected route before inference. The client omits transcripts, raw rows, report files, credentials, private URLs and Incognito alias maps. Both apps exclude payloads and links from routine telemetry and enforce access when a receipt is reopened.

Related implementation detail is in the [Discovery handoff](splunk-discovery-tool-handoff.md) and [Constellation design](constellation-mcp-design.md).
