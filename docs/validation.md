# Release evidence

Current release: **Constellation 1.0.1 / build 61**, qualified October 30, 2026. The patch retains the bounded Enterprise support profile. The earlier [1.0 record](reference/validation-1.0.md) preserves the original runtime, failures and upgrade/rollback evidence. Private hosts, keys, indexed rows, user files and lab screenshots remain outside Git.

## 1.0.1 — October 30, 2026

The qualified candidate bytes are retained for the 1.0.1 release. These patch checks supplement the earlier 1.0.0 qualification below.

| Item | Recorded result |
| --- | --- |
| Package | 1.0.1 / build 61; SHA-256 `8f875e0a204630589df32c1bec8b8d4e6e4d50d49fd01b6951c38617b4b79515` |
| Archive | 545 regular files / 5,574,733 bytes; one app root; no macOS sidecars or extended tar metadata |
| Release | [v1.0.1](https://github.com/LeiterConsulting/constellation/releases/tag/v1.0.1) |
| Installation | Same archive on Enterprise 10.2.8 and 10.4.4; no restart required |
| Offline checks | 637 Python / 151 frontend tests passed; Node 22 production build and browser budget passed |
| AppInspect 4.2.1 precert | 0 errors / 0 failures / 0 future failures; 7 warning checks / 1 skipped |
| Repeated ordinary-author flows | Three two-page creation/edit cycles per provider: OpenAI, Ollama and managed AITK; all nine completed with exact draft reopen and private native definition readback |
| Recovery | One OpenAI creation used the existing bounded repair loop; the other seventeen cohort turns completed without repair. Temperature-cutoff and independent-measurement probes passed separately |
| Page scheduling | An existing eight-page, 65-tile, 32-source operational dashboard reached later-page sources, including graph auxiliary sources and dynamic inputs; original definitions and conversation remained unchanged |
| Browser flows | All three providers: selected-table chat edits, live preview rows and overview/detail/return navigation; normal Studio rendering and row/return checks. An edited AITK draft also passed the app’s save-private-copy dialog and exact native readback |
| Save diagnosis | A controlled response disconnect was confirmed by exact readback/receipt. A real stale-browser conflict retained the winning revision; the existing save-as-new action preserved the browser's work |

The cohort used direct OpenAI **gpt-6-luna**, Ollama **qwen3-coder:latest** and the existing managed AITK connection. Creation took approximately 28–46 seconds for direct OpenAI, 14–28 seconds for Ollama and 26–30 seconds for AITK in this small concurrent lab exercise. These are observed samples, not a latency guarantee or comparison of equivalent models/hardware. Ordinary authors had no native credential-store capabilities.

The preview retains 200-row/five-second query limits and an eight-consumer-source bound **per active page**. Capped operational and detail results remained partial. Page switching was exercised in the browser; late-result exclusion, effective-token caching, expiry and input/error distinctions also have offline regression coverage.

The recent-pointer failure is a reproduced post-commit failure path, not a confirmed explanation for every earlier save conflict. Its fix keeps an already verified primary save successful. True concurrent edits still require preserving both versions. The patch does not change native document schema, query/measurement validation, draft schema 3, portable format 5 or credential permissions. Temporary authors, the copied provider key and private test objects were removed; existing administrator settings and the operational demo were preserved.

The AppInspect warnings cover bundled Splunk library telemetry, Python compatibility notices, admin-only Cloud role differences and a vendor schema's example IP string. They do not establish Cloud approval. This remains bounded single-search-head Enterprise qualification, without a new independent review, SHC coordination or complete Studio parity claim.

## 1.0.0 — October 29, 2026

### Qualified package

| Item | Recorded value |
| --- | --- |
| App | 1.0.0 / build 60 |
| SHA-256 | d53d62e3ce929a5a912cd1d6dccddaecbdee96d65a35d7b4a4a7f44cb0ddebc7 |
| Archive | 497 regular files / 5,548,484 bytes; one app root |
| Target A | Enterprise 10.2.8 / Studio 1.23.12 |
| Target B | Enterprise 10.4.4 / Studio 1.26.6 |
| Deployment | Single Linux Enterprise search head |
| Release | [v1.0.0](https://github.com/LeiterConsulting/constellation/releases/tag/v1.0.0) |

The release app bytes were not rebuilt for the documentation refresh. Documentation images are [synthetic local UI captures](screenshots.md), separate from qualification.

### What was checked

| Evidence | Result | What it establishes |
| --- | --- | --- |
| Offline suites at runtime qualification | 620 Python / 143 frontend tests; TypeScript and Node 22 build passed | Authored fixture and implementation regression checks |
| Release-source CI | Python 3.9/3.13, frontend/package and secret-scan passed on [release commit](https://github.com/LeiterConsulting/constellation/commit/f46530ab59f6ed03db2d36076b66c450b593059e) | Exact source publication gates; not live integration |
| AppInspect precert | 0 errors / 0 failures / 0 future failures; 7 warnings / 1 skipped | Local precert results; not Cloud certification |
| Three-provider core | 15 completed model turns across ordinary authors, one call per turn | Selected multi-page creation, sparkline/element edits and report-context preservation |
| Additional operational datasets | Six creation/edit flows / twelve turns; controlled response-loss recovery | Selected actual-data queries, partial labels and no-replay delivery recovery |
| Second-target AITK 6.1 | Two-page application-data creation, table/return edits and browser chat/reopen passed | A protected configured connection worked without ordinary credential access |
| Native output | Rendering, input changes, row/detail/return navigation and private readback passed | Specific native cases on recorded versions; not all Studio options |
| Management and sharing | Native CRUD/XML restore, draft CRUD, authorized viewer access and shared-edit refusal passed | Selected ordinary-user and native ACL behavior |
| Cancellation/recovery | All three providers passed model-stage Stop with no late applied result | Cooperative app cancellation, not guaranteed upstream termination |
| Upgrade/rollback | 0.43 → 1.0 → 0.43 → 1.0 on both targets | Exact recorded draft/history/conversation/pending-file/token/native/preference preservation |
| Packaging/privacy | Archive and Gitleaks/publication checks passed; test users/keys/objects cleaned up | Reviewed artifact hygiene and bounded cleanup, not proof of no possible vulnerability |

The direct models were OpenAI **gpt-6-luna** and Ollama **qwen3-coder:latest**. AITK 6.1/6.2 used **OpenAI gpt-5-mini**, with a recorded **16,000-token / LOW** configuration. Connection tests and authoring qualification are separate; other models are not automatically covered.

### Interpretation and retained failures

Capped live previews in the operational-data cohort remained labelled **partial**. Tiny synthetic transformation probes separately checked missing-value/count/temperature rules. Neither result proves every business calculation is correct.

The detailed record preserves preparatory harness errors, superseded candidates and AITK 6.1 vendor update/delete HTTP 500s. The uncertain vendor mutation was not blindly replayed; its exact temporary record/credential were verified and removed under administrator authority. Existing user work and protected primary configuration were preserved.

Human/independent reviews remain follow-up work. No unaided-user success rate, independent human security audit, full native parity, production SLA, SHC coordination or Cloud approval is claimed.

### 1.0.0 technical release candidate — October 29, 2026

This heading preserves the original qualification link. Read the [complete dated 1.0 record](reference/validation-1.0.md#100-technical-release-candidate--october-29-2026). The accepted candidate bytes were published unchanged.

## Earlier evidence

The [validation history](history/validation.md) retains every earlier dated section, package hash, failed candidate and bounded rerun. Development milestones are not all separate releases. The [changelog](../CHANGELOG.md) identifies included increments.

## Documentation assessment

The [documentation review](documentation-review.md) records the 1.0 editorial/content audit, image provenance, link checks and downloadable-guide verification. Those checks improve the documentation; they do not requalify unrelated runtime behavior.

**Next:** [Support scope](support-policy.md) · [Native coverage](native-coverage.md) · [Technical checklist](v1-readiness.md)
