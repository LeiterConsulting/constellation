# Detailed 1.0 qualification record

Recorded October 29, 2026. These are sanitized operated/offline results, not independent human acceptance or a general success-rate estimate. Use the [current release summary](../validation.md) for navigation.

## 1.0.0 technical release candidate — October 29, 2026

Qualified release package: **1.0.0, build 60**, SHA-256 `d53d62e3ce929a5a912cd1d6dccddaecbdee96d65a35d7b4a4a7f44cb0ddebc7`. Its **497 regular files / 5,548,484 bytes** share one app root, without macOS sidecars/resource forks, PAX metadata, runtime-local configuration or the build manifest. The final archive, installed provider/native checks and upgrade cycle refer to these exact bytes. Runtime-source, module/CSS references and browser loading were checked separately from archive hygiene. The preceding candidate `a60994361bf174332d0f1dcc0ed80481ba410668cfe68e3a3ab5831394535330` retains its local evidence and is superseded by the stricter compound-request guard.

The release profile is a **single Linux Enterprise search head**, qualified on Enterprise **10.2.8 / Studio 1.23.12** and Enterprise **10.4.4 / Studio 1.26.6**. Human/independent reviews are non-blocking follow-up work under the product owner's decision; this does not qualify Cloud, SHC, arbitrary models or complete native parity. See the [technical checklist](../v1-readiness.md).

### Offline, package and startup checks

- **620 Python tests and 143 frontend tests passed**, with TypeScript checking and the Node 22 production build. Python 3.9 and 3.13 are also required by PR CI. Fixtures remain synthetic and require no live credentials.
- AppInspect precert: **0 errors, 0 failures, 0 future failures, 7 warnings and 1 skipped check**. Warnings/manual certification are not represented as Cloud approval.
- Eager JavaScript is **1,660,419 bytes / 503,444 gzip**, about **91% below** the prior eager renderer bundle. The build gate measures transitive static imports, deduplicates shared chunks and requires a deferred renderer, with limits of 2.5 MB raw / 750 KB gzip. The deferred renderer still has a large chunk warning; its bytes were deferred, not removed.
- Content-hashed entry, lazy/shared module and CSS names survive packaging. Both installed targets loaded the final preview/native output; a renderer-load boundary preserves the draft and conversation with explicit recovery guidance.
- Repository publication checks and package Gitleaks passed. Staged/history and documentation-bundle checks are part of publication; exact-head CI must pass before merge/release.

### Ordinary-author provider regression

The primary target used direct OpenAI **gpt-6-luna**, Ollama **qwen3-coder:latest**, and shared AITK **6.2 / OpenAI gpt-5-mini**, retaining a **16,000-token / LOW** connection. Every provider passed a complete two-page actual-data freezer/sparkline creation, a selected all-row sparkline style/width edit, a private lookup/macro-backed selected edit, and foreign-report title/calculation edits retaining original context and native chains. These **15 completed model turns used one model call each**. Gap-policy clarification used zero model calls. Draft/conversation/scope reopen and private native definition readback passed.

| Provider | Two-page creation | Selected sparkline edit | Report title / calculation |
| --- | --- | --- | --- |
| Direct OpenAI | 29.36 s | 5.64 s | 3.20 / 4.36 s |
| Ollama | 23.92 s | 7.73 s | 17.15 / 12.90 s |
| AITK 6.2 | 26.29 s | 17.84 s | 15.11 / 14.94 s |

Two further real operational datasets exercised response/duration and packet-loss summaries and trends, followed by exact selected-table title edits. All **six creation/edit flows / twelve model turns** passed with one call per turn. Creation ranged **12.77–30.02 s** and edits **4.55–23.30 s**. Every edit deliberately lost the original REST response after send and recovered only the original validated reply, then acknowledged it; inference was not replayed. These capped live previews remained honestly labelled **partial**. Separate tiny synthetic inputs checked unknown-versus-zero means and source-observation counts; they are analytical property tests, not indexed production data.

The second target passed actual application-duration multi-page creation, selected-table and return-button edits through securely configured **AITK 6.1 / gpt-5-mini, 16,000 tokens / LOW**: **29.56 / 15.75 / 15.30 s**, one call each. A further installed-browser chat edit changed exactly the selected report-backed table title, updated the preview, preserved its current input, saved the conversation and survived refresh. These bounded samples are operated regression evidence, not unaided-user trials, a general success-rate estimate or a latency SLA.

### Native, recovery, storage and isolation

- Selected-source inspection resolved default/current/unset tokens and a report-backed chain in its original app. Synthetic default/current selections returned **2 / 1 rows**; unset required input waited. Metadata excluded event values/current token state. The unchanged inspection UI was also operated before the final report-eligibility tightening: it followed the selected source and changed counts after a native input change. Final-package browser checks separately exercised renderer loading, chat, native output and reopen.
- Native Studio rendered final-package freezer tables, area sparklines, trends, device-row/tab navigation and return on the older target. The newer target rendered report-chain input changes and an actual-data multi-page application dashboard with row/detail/return navigation. These ran as normal native dashboards outside the Constellation workspace.
- Stop during the real model stage passed on all three providers: control responses **0.035 / 0.040 / 0.035 s**, no late applied reply, no post-cancel repair/search, and unchanged saved draft. Upstream inference may still finish or incur charges; this is cooperative app cancellation.
- Signed native search poll/cancel, immediate cancel, app/user/session tampering and private-peer denial passed on both targets. Compatible report/chain/CSV/macro transfer retained native context, distinct same-named dependencies and fresh private destination objects.
- Ordinary-owner native rename/delete/complete-XML restore and draft rename/duplicate/Trash/restore passed. An authorized administrator shared only a disposable native view through normal Splunk ACLs; an ordinary viewer could read/duplicate it, while shared rename/delete remained refused. Private ACLs were restored. A standard author without native sharing authority was correctly denied publishing an app-shared view; no role expansion was used to bypass that denial.
- The real **0.43 → 1.0 → 0.43 → 1.0** app-update cycle passed on both targets, preserving exact drafts, conversations, history, pending synthetic files, tokens/focus, native XML/privacy, provider preferences and active draft. This is upgrade/rollback on existing Enterprise installations plus clean-author first use, not a fresh untouched server or SHC qualification.
- Refresh during a pending composer save recovered the unsent text without inference replay. Light/dark previews and compact 900×720 composer/control access were operated in the browser. This is bounded UI inspection, not a complete accessibility audit.

### Setup, retained failures and cleanup

Second-target AITK setup added only the missing discovery capability to an existing trusted maintainer, restricted both backing collection writes to trusted maintainers while preserving read ACLs, and used a dedicated inference-only author role. Ordinary authors remained unable to read stored credentials or manage connections. These deliberate secure administrator setup changes are distinct from unchanged primary-user work.

Retained preparatory failures include a missing report-test fixture, an invalid synthetic native saved-report token expression, a live-preview grader that incorrectly required complete results under the existing caps, a private ACL represented as null rather than explicit empty grants, and a UI-message count that omitted the welcome message. They were corrected in ignored harnesses without relaxing app validation. Some early held-out creation calls had already succeeded before the incorrect partial-result assertion; do not count those attempts as failures before inference or erase them from the evidence.

AITK 6.1's vendor connection update/deletion paths returned HTTP 500 during setup/cleanup. Inference itself passed. The failed mutation was not blindly replayed. The exact temporary connection record and its referenced credential were verified by unique name, source reference and native ACL metadata and removed under administrator authority; the original disabled policy was restored. No vendor code was patched or unrelated connection/credential removed. Vendor editor/lifecycle defects remain administrator/vendor issues, not an app-managed lifecycle claim.

All disposable accounts, copied keys, drafts, native views, lookup/report/macro fixtures and test preferences were removed with readback checks. Original primary administrator settings, **36 drafts / 78 configuration-content hashes**, protected AITK policy/backing ACLs and existing provider configuration were preserved. The secondary target intentionally retains trusted maintainer discovery and restricted backing writes; its temporary inference policy/connection/key are removed. Detailed local evidence remains ignored.

The technical candidate closes the declared 1.0 checks for this profile. Broader native options, every business-rule/SPL2/import combination, different models, production-duration reliability, independent-user/security/accessibility review, Cloud certification and distributed coordination remain explicit follow-up work. Nothing in this version labels those as completed.
