# Upstream licenses and notices

Constellation's MIT license covers first-party code and documentation. Upstream components retain their own terms; these files are upstream notices, not first-party MIT grants.

The app packager collects license filenames without depending on case, including LICENCE.md and LICENSE-MIT.txt, and retains NOTICE, CopyrightNotice.txt and ThirdPartyNoticeText.txt. It does not fetch licensing material during a build.

Some published npm archives omit a standalone license. The [manifest](license-manifest.json) pins those package versions, notice hashes and primary sources. It includes verbatim README license sections, unmodified repository notices and the following explicit reconstruction:

- temporal-polyfill 0.1.1 declares MIT and copyright 2022 Adam Shaw in its published package.json. Its notice combines those declarations with the standard MIT text. The unmodified ECMA specification notice from its version tag is retained separately.
- tr46 0.0.3 declares MIT in npm metadata but omits a license file. Its notice comes from the first LICENSE.md commit in the same upstream repository; that provenance remains explicit.

A missing notice for a new installed package/version fails packaging until reviewed. Updating dependencies requires checking their notices and this manifest; do not silently reuse a fallback for a newer version. This is a technical attribution review, not an independent legal audit.

The release's third-party-notices ZIP and the handoff include the collected material. Keep the notices supplement and MIT LICENSE with redistributed original installers. Future source builds embed both. The existing qualified installer bytes and runtime tag remain unchanged.
