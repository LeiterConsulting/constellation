# Constellation identity

The approved mark combines a three-panel dashboard canvas with a connected data path ending in a creation spark. The source was created with built-in image generation and selected by the app owner. `constellation-master.png` is the transparent source; the export script preserves its silhouette and produces the technical sizes. The source and this development tooling are outside the installed app.

The in-app heading uses the mark's alpha channel as a CSS mask with the inherited Splunk text color. It follows the app theme and introduces no extra control or repeated screen-reader label. Its visible title remains ordinary text.

Native launcher/menu files use a white mark on an ink backplate with transparent outer corners, keeping their internal contrast consistent across host backgrounds. The neutral backplate is part of the raster export, not a replacement for Splunk theme tokens in the app UI. `appLogo` includes the Constellation wordmark on the same backplate.

| Shipped file in `splunk/constellation/static/` | Pixels | Purpose |
| --- | --- | --- |
| `appIcon.png` | 36 × 36 | Standard launcher icon |
| `appIcon_2x.png` | 72 × 72 | High-density launcher icon |
| `appIconAlt.png` | 36 × 36 | Standard app-menu icon |
| `appIconAlt_2x.png` | 72 × 72 | High-density app-menu icon |
| `appLogo.png` | 160 × 40 | Classic app bar |
| `appLogo_2x.png` | 320 × 80 | High-density classic app bar |

These sizes and static-file names follow [Splunk's asset requirements](https://dev.splunk.com/enterprise/docs/developapps/manageknowledge/configureappproperties/). The source exports contain no external URL or runtime image service.

## Native navigation

The bespoke mark is app branding, including the launcher assets on newer hosts. Native navigation-item glyphs are a different surface: the 10.4 `icon` attribute on links accepts [named Splunk icons](https://dev.splunk.com/enterprise/reference/dashboardnav/), not an arbitrary PNG or SVG URL. The transparent marks below can be used in Constellation-owned UI, but are not a way to inject custom art into Splunk's sidebar.

| Existing destination | Splunk 10.4 name | Splunk 10.6 name |
| --- | --- | --- |
| Workspace | `chartpanels` | `ChartPanels` |
| Dashboards | `layerstriple` | `LayersTriple` |

The [10.4 release notes](https://help.splunk.com/en/splunk-enterprise/release-notes-and-updates/release-notes/10.4/modern-navigation-ui-changes) define the original named set. The [10.6 release notes](https://help.splunk.com/en/splunk-enterprise/release-notes-and-updates/release-notes/10.6/modern-navigation-ui-changes) allow the React icon library's exact case-sensitive names and retain the older names. The 10.4 names are the conservative common mapping; the table does not claim qualification on future versions. These choices are recorded in [native-navigation.json](native-navigation.json), explicitly marked as mapping only.

The existing Simple XML host and its default-view navigation are preserved. Activating a modern navigation host is a separate framework change: [Splunk's guide](https://dev.splunk.com/enterprise/docs/developapps/createapps/addnavsplunkapp) specifies the modern `react-page` integration. Do not add undocumented icon attributes to `<view>`, replace the default home route, or patch native navigation CSS just to insert this mark. Verify classic and modern host placement on the target versions when the branding is installed.

## Banner and presentation kit

The banner illustrations extend the selected mark's panel/path/spark language. They were made with built-in image generation; their final lettering, exact-size exports and small marks use the export script. The flat monochrome mark remains the canonical identity. The softly raised banner illustration is decorative artwork, not a replacement mark or a screenshot of the app.

| Files under `exports/` | Pixels | Intended placement |
| --- | --- | --- |
| `banner-dark.png`, `banner-light.png` | 1600 × 640 | Documentation or an introductory page |
| `banner-compact-dark.png`, `banner-compact-light.png` | 1600 × 400 | Compact documentation/release banner |
| `wordmark-dark.png`, `wordmark-light.png` | 640 × 144 | Transparent lockup for the named background |
| `social-dark.png`, `social-light.png` | 1200 × 630 | Repository social preview, uploaded separately |
| `listing-splash.png` | 623 × 350 | Splunkbase splash artwork, not a live screenshot |
| `mark-dark-{size}.png`, `mark-light-{size}.png` | 20, 24, 32, 48, 512 square | Transparent identity at small and large sizes |

`dark` means white artwork for a dark background; `light` means ink artwork for a light background. The 20/24-pixel marks are for identity, not new action buttons. Keep ordinary actions on recognizable Splunk icons with accessible labels. Do not turn the creation spark into an ambiguous unlabeled control.

The [Splunkbase file standards](https://dev.splunk.com/enterprise/docs/releaseapps/splunkbase/approvalcriteria/) specify 623 × 350 for a screenshot or splash screen. Other banner dimensions above are Constellation presentation choices, not Splunk platform requirements. No marketing artwork is installed in the app package: only the six native PNGs and the bundled title mask are shipped. The working canvas receives no large banner, new navigation entries or extra controls.

Use image alt text such as "Constellation — From question to dashboard" when a banner communicates the title. Use empty alt text when it is purely decorative beside an equivalent text heading. Keep actual interface headings as text and continue using Splunk theme tokens for their color. Avoid stretching or tightly cropping the mark; preserve transparent padding. Marketing neutral colors are baked into image assets and do not override the app theme.

The editable inputs are `constellation-master.png` and the two generated sources in `sources/`. Their prompts are retained in `generation-prompt.txt` and `sources/banner-prompts.txt`. No live data or user screenshots were used. The export [manifest](exports/manifest.json) records each output's dimensions, alpha, purpose, package status and SHA-256 hash.

## Re-exporting

Run `node scripts/export_branding.cjs` from the checkout. It needs Sharp in the development tools; this is not a new app/runtime dependency. If Sharp is supplied outside the checkout, set `CONSTELLATION_SHARP_MODULE` to that module's location. Use a Node binary matching Sharp's CPU architecture.

The script writes the six native files above, `src/assets/constellation-mark.png`, the presentation kit and its manifest. It performs monochrome alpha cleanup, padding/resizing and raster typesetting/composition. It does not regenerate or redesign the selected symbol. Sharp uses the local Arial/Helvetica font fallback for lettering; a different system's font substitution can change text-export hashes. Keep the approved sources and reviewed exports together. Rebuild the frontend after exports, and increment the normal app build when distributing an update so Splunk refreshes static assets.

Check the mark at 24, 36 and 72 pixels on both themes and inspect the wordmark at native size. Local browser checks and packaging are distinct from installed pre/post-10.4 acceptance. A branding update does not requalify unrelated provider or native Studio behavior.
