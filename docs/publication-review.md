# Public-repository review

Reviewed October 29, 2026, before the owner's visibility change. The source/history baseline is commit c469f91. This review does not change repository visibility, native qualification or the supported deployment profile.

## Checks and findings

| Surface | Reviewed scope | Result |
| --- | --- | --- |
| Git | 68 reachable commits, all fetched branches/tags/PR heads, 1,478 unique file blobs | No publication-policy or secret findings; author/committer emails use GitHub addresses |
| Images | 32 unique image blobs | Branding and authored fixtures; the four local UI screenshots retain their synthetic-data captions and provenance |
| Published downloads | Seven releases, 30 original assets, archive members and checksums | No private-lab identifiers, secret findings, macOS sidecars, unsafe members or digest mismatches |
| Actions | All 277 available runs, 1,625 log files; zero uploaded artifacts | No secret/private-lab findings; home-path matches were GitHub runner/Dependabot container paths |
| Discussions | All 16 issue/PR bodies, available discussion/review comments and release notes | No publication-policy findings |
| Dependencies | Current npm audit, including development dependencies | Zero reported vulnerabilities at review time; not a guarantee against undisclosed or future issues |
| Workflow authority | Repository default and committed workflow permissions | Read-only default; workflows cannot approve pull requests; no live provider/lab credentials are required |
| Licensing | MIT declaration plus installed upstream licenses/notices | Fixed omitted filename variants, README-based declarations and attribution files; sources and exact versions are [recorded](../third_party/README.md) |
| Current prose | README, installation/sharing/contribution guidance | Removed unconditional private-visibility assumptions; historical status remains labelled |

The corrected collector includes all discovered upstream license/NOTICE files and requires reviewed, hash-pinned fallbacks for installed packages that omit a standalone license. The dependency supplement accompanies the original installer and is included in the handoff. Future builds embed it. The existing installer and v1.0.0 runtime tag remain unchanged; a file comparison verified that packaging changes do not alter runtime files.

All seven published tags have the same pinned non-development dependency paths/versions. The reviewed notices therefore also accompany earlier installers; their original archives and historical qualification remain intact. Older versions are not separately maintained.

The six new packaging tests cover alternative names, multiple notices, missing notices, exact fallback versions/hashes, symlinks and deterministic/checksummed supplements. Full regression, CI and publication scans apply to the preparation commit. Raw receipts, logs and downloaded archives remain local.

## Owner steps at the visibility change

The repository is still private at this review. Its main branch is unprotected, Dependabot security alerts report disabled, and private vulnerability reporting is unavailable on the private repository. These settings are not inferred from the presence of CI or Dependabot version-update PRs.

After making it public:

1. Enable **Private vulnerability reporting** and confirm the **Report a vulnerability** form works. Enable or confirm **Dependabot alerts**, **secret scanning** and **push protection**. These are separate settings; version-update PRs alone do not enable vulnerability alerts. GitHub documents [private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) for public repositories.
2. Protect **main** with required checks: **python (3.9)**, **python (3.13)**, **frontend-and-package** and **secret-scan**. Block branch deletion and force pushes. Choose a PR/reviewer policy appropriate to the number of maintainers; this review does not impose a second reviewer on a solo maintainer.
3. Check the repository and latest release signed out: README images, documentation links, all downloads and checksums, issue forms and the private reporting route. The authenticated pre-public review cannot prove anonymous access.

GitHub makes [Actions history and logs public with the repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility). Existing logs were reviewed here; future workflows and issue attachments still need the same publication discipline.

No further content/package publication blocker was identified in this scope. This is not an independent security/legal audit, unaided-user acceptance, Cloud certification or a claim of complete Studio parity. Keep the [support profile](support-policy.md), [security guidance](../SECURITY.md) and [release evidence](validation.md) with public distribution.
