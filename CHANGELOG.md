# Changelog

This repository begins with the 0.7.1 development preview. Version history below summarizes implemented behavior; it is not a record of production releases or certification.

## 0.8.0

- Track short-lived current-user preview jobs, including completion, truncation, resource finalization, cancellation and stale snapshots.
- Keep a user-editable dashboard brief independent of the rolling conversation, with verified scope and page purposes supplied separately.
- Retain up to ten material dashboard versions within a 4 MB history budget; restore across refresh/reopen while keeping the current conversation.
- Migrate older drafts sequentially to schema 3 without rewriting unknown future formats.
- Simplify secondary controls under More and replace misleading pending-search error panels with a waiting state.
- Check explicitly named row-drilldown destinations and verify table handler fields against search output.
- Accept equivalent simple dataset-prefix formatting while rejecting broader search scopes; provide source-specific repair feedback.
- Distinguish OpenAI timeouts from connection failures, with a bounded 90-second generation wait and no blind transport retry.
- Add synthetic journey regressions across recovery, focus edits, navigation, draft switching, revision restore and failure preservation.

## 0.7.1

- Persist the last-opened draft independently from document edits.
- Infer an unambiguous supported time window for direct blank-canvas requests.
- Reuse unchanged search previews and inspected UI field metadata.
- Match the one-shot result request to the 200-row preview budget.
- Protect chart/input placement and native navigation-button label height.
- Improve selection scrolling, build progress and recovered response copy.
- Add reviewed repository documentation, publication checks and CI.

## Earlier development milestones

- **0.7.0:** bounded automatic recovery, typed pages/navigation and directed element selection.
- **0.6.x:** private persistent drafts/conversations, recoverable library management, actual-data grounding and search validation.
- **0.5.0:** blank-canvas creation and contextual prompts.
- **0.4.0:** native PDF interaction exercises, Ollama and AITK adapters, retained provider connections and modality guards.
- **0.3.0:** broader native definition authoring and image/sketch interpretation.
- **0.1.x–0.2.x:** embedded Studio renderer, canvas/conversation shell, native copy saves and direct OpenAI Settings.

See [validation scope](docs/validation.md) and [release gates](docs/roadmap.md) for the limits of these milestones.
