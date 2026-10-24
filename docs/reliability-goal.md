# Reliability milestone: 0.8

Build a reliable, useful conversational Dashboard Studio authoring app within the Splunk app boundary. Keep the canvas, conversation and element selection as the primary experience. Reveal supporting detail when requested.

Deliver verifiable search completion with cancellable, resource-bounded jobs; a durable, user-editable dashboard brief for purpose, audience, units and exclusions; and previous dashboard versions that survive refresh and reopen. Use server-verified data scope and page purposes alongside the brief during authoring and automatic recovery. Preserve current work on any failure.

Verify the complete path: create from real Splunk data, recover a rejected proposal, refine a selected element, navigate between pages, switch to another draft, reopen and restore a prior version. Run synthetic regression fixtures, supported Python and frontend checks, build/package inspection and live lab exercises. Keep raw lab evidence, credentials and user material outside Git. Commit and push reviewed source to the private repository and verify CI.

Success means honest complete/partial/stale/failed feedback, persistent requirements and recoverable drafts through representative journeys. Ninety percent unaided completion is a future measured usability target, not a claim established by scripted fixtures or developer testing.

The evidence and remaining qualification gates belong in [validation](validation.md). Provider adapters, compatibility contracts, search lifecycle, brief handling, history retention and migrations remain independently updatable modules; see [architecture](architecture.md) and [upgrade guide](upgrade-guide.md).
