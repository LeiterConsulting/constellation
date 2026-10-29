# Documentation standards

Write for the task the reader is trying to complete. Product instructions belong in current guides; engineering history belongs in reference/history records.

## Structure and language

- The repository README explains the product, download, first steps, scope and where to get help.
- The documentation index separates author, administrator and contributor paths.
- Each task has prerequisites, exact visible controls, expected result and a recovery link.
- Keep app preview, native Studio and stored drafts distinct.
- Use concrete statements. Avoid superlatives, unsupported ease/speed claims and implied endorsements.
- Link a capability to source, a test contract or dated qualification. Inventory, mocked tests, operated flows and independent acceptance are different evidence.
- Label history, synthetic examples, unqualified combinations and native-only behavior.
- Do not hide a known failure by replacing its historical record with a passing rerun.

## Images and downloadable guides

Use unretouched actual UI captures from the authored local example. Never commit live lab/user screenshots. Keep captions and the image manifest together; identify unsent prompts and unavailable local-only controls. Branding illustrations are not product screenshots.

The Markdown user guide is the editable source for its PDF. Regenerate, render and visually inspect the PDF after changes. Bundle referenced local files, verify links in the extracted handoff, and keep generated artifacts outside Git.

## Release maintenance

A documentation-only refresh may replace documentation assets/checksums on the release, with its source revision recorded in the notes. Preserve the qualified app archive exactly. Do not move an existing runtime tag or silently imply new runtime qualification.

Run the documentation checker, repository checks and Gitleaks before publishing. Check release links/downloaded bytes afterward. Future code/UI changes must update affected instructions, screenshots and factual claims alongside their tests.
