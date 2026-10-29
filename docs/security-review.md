# Privileged handler review - October 25, 2026

## Scope and independence

A fresh agent reviewed the 0.15.0 baseline (`796212bf0b2a5017e31a31176fc29ab269d288ac`) without changing files or using lab credentials. It examined caller authorization, system-token separation, fixed query construction, connection trust, cancellation, admission, errors, packaging and relevant tests. After implementation it independently reviewed the patches and the new owner-only OpenAI boundary, including AITK 6.2 vendor resolution/ACL behavior. This is an independent agent source review, not a third-party audit, penetration test or Splunk Cloud approval.

## Findings and disposition

| Finding | Impact / precondition | Fix |
| --- | --- | --- |
| Conditional P2: approving a connection by name did not establish who could change its resolved endpoint/configuration. | An allowed author with write access to the named connection or its backing configuration could redirect privileged inference. The source review did not demonstrate credential exposure in the lab. | A separate metadata guard checks both fixed AITK collections, the modern record's write ACL and trusted owner, trusted execution user, duplicate/legacy precedence and supported provider resolution. Unsafe or unavailable metadata fails before job submission. |
| Execution namespace was syntactically valid but not checked as a trusted maintainer. | A mistaken ordinary-user namespace could own/read other users' shared prompt-bearing jobs. | Verify the execution user's maintainer role before constructing a worker. |
| Missing explicit native REST transport deadlines. | A stalled request could outlive the polling deadline/admission receipt. | Explicit transport timeouts, plus accurate documentation that admission receipts are not a strict quota on all native jobs after uncertain dispatch or process failure. Cleanup remains best effort. |
| Security text incorrectly denied all system authentication. | Deployment reviewers could misunderstand the privilege boundary. | Name both privileged handlers explicitly; main/control remain caller-only. |

The reviewer found no direct caller-controlled SPL, execution-user, SID, system-token disclosure or cross-user authorization bypass in the reviewed fixed AITK flow. Follow-up review identified no remaining actionable security finding in the reviewed patches.

## Owner-only OpenAI custody

The user requested ordinary-author OpenAI setup without credential-store capabilities. A separate handler derives the exact encrypted record ID/namespace from the verified caller, checks ownership/privacy before reads or writes, restricts an empty placeholder before storing a first key, and returns only settings metadata. The saved key stays within the privileged handler for fixed official model discovery and structured inference. Request/model/token/file guards remain in force; tools, remote file references, arbitrary URLs/owners/resources and provider-side conversation references are rejected. The reviewer identified no actionable security issue in this boundary. Its minor provider-name error in busy guidance was fixed and tested.

No credential permissions were granted to ordinary authors. Existing owner-private encrypted records and owned legacy IDs remain in place. The app does not patch vendor files or create an external runtime. AITK connection/provider settings outside the reviewed modern-record resolution remain unsupported on shared inference until explicitly reviewed.

## Evidence and limits

Synthetic tests cover caller substitution, unsafe policy/record/collection ACLs, ordinary execution namespaces, legacy shadowing (including custom provider keys), ambiguous/malformed metadata, prompt encoding, key presence projection, invalid replacement, unsupported operations/models/files, token separation and native timeout forwarding. The reviewer separately reran targeted tests; the full offline and installed results are recorded in [validation](validation.md).

Live evidence stays local. Only reviewed summaries are published. Production roles, network/egress controls and retention remain administrator responsibilities. Distributed search-head behavior, broader vendor/model combinations and Cloud approval need separate deployment qualification. External/independent review is follow-up work under the product owner’s 1.0 decision; it is not recorded as completed or required to release the bounded [supported profile](support-policy.md). Privileged handlers must be reviewed again when their authority, schemas or vendor resolution changes.

## 0.18 delivery boundary

The earlier independent privileged-handler review does not cover this later change. The new unprivileged delivery helper temporarily retains an already validated reply under the original session-signed run handle. Deterministic tests cover different users/sessions, replay denial, Stop before/after completion, expiry, acknowledgement, cache bounds and disk-failure fallback. Source review retains caller-only main/control authentication and introduces no provider/credential route or search authority. Replies can include the user's dashboard/SPL and brief/goal; restrictive local files and bounded retention are required. See [the storage contract](reference/design-notes.md#delivery-recovery-018). These checks are not a new independent security audit, Cloud approval or cluster qualification.

The 0.18 source review also found that signature validation alone did not compare the run record's stored owner. A caller can know its own native session key and could re-sign a learned foreign nonce. Every run read/mutation now checks the stored session owner as well; cross-user and same-user/different-session re-signing fixtures must be denied without changing either receipt or reply. This is a required check, not reliance on nonce secrecy.


## 0.38 asset and dependency boundary

This increment received source review and synthetic/live permission checks, not a new independent audit. Native SVG inspection is current-user GET to a fixed image collection with bounded ID metadata; artwork bytes remain outside inference. Same-origin packaged-media export rejects redirects, traversal, dynamic paths, oversized bodies and active SVG; its fetches never accept a caller-supplied external origin. Portable import validates the file and destination dependencies before shared mutations and never replays uncertain uploads. Report inspection/inclusion reads only the caller’s visible report, never dispatches as its owner and copies only explicit compatible read-only searches. Lookup contents, macro definitions, extension code, credentials, schedules and permissions are not migrated. Main/control and privileged provider authority remain unchanged. This checklist is incomplete for general SPL dependency graphs; review statuses must not be presented as verified equivalence.
