# Update and recover Constellation

This guide covers the 1.0 app update boundary. It is not a promise that every earlier release can safely read newer drafts.

## Before updating

1. Record the installed Constellation/Splunk/Studio/provider versions.
2. Retain the exact current installer and its checksum.
3. Back up owned drafts/conversations, native dashboards, administrator configuration and encrypted credential storage through the approved Splunk backup process. Preserve its ACLs and encryption context; never place credentials in a distributable package.
4. Wait for drafts to save and finish or stop active authoring.
5. Review the destination release's [support scope](support-policy.md) and [validation](validation.md).

Removing the app or its private configuration can remove drafts, pending attachments, history and Trash. An exported native dashboard or portable file is not a complete draft/conversation backup.

## Install the update

Use **Install app from file** in Splunk app management and deliberately select its update option. Follow the instance's restart indication, then refresh old workspace tabs.

Constellation 1.0 retains **draft schema 3** and **portable format 5**. No credential, draft, media or native-view migration runs for the qualified 0.43-to-1.0 path. Content-derived browser/handler names prevent stale assets and workers, but a version label alone does not prove the new runtime loaded.

## Verify after updating

As an intended ordinary author:

1. Reopen a draft and its conversation, brief, page/input state and pending files.
2. Inspect a selected source and refresh its bounded preview.
3. Make one focused edit and verify unrelated work remains.
4. Confirm provider settings and the selected connection still work.
5. Save a new private native copy and inspect it in Studio.

Do not use a passing administrator test as ordinary-user permission evidence.

## Rollback limits

The recorded app-update cycle was **0.43 → 1.0 → 0.43 → 1.0** on the two qualified single-head targets. Exact draft/history/conversation/pending-file/token/native/preference preservation passed. **0.43 was an unpublished qualification baseline, not a release download.** This does not qualify rollback to the published 0.34 archive, an arbitrary older version, a fresh server or SHC.

Use an administrator-approved recovery plan and retained compatible archive/backups. Do not install an older writer against newer records unless that exact schema path is qualified. Schema-2 writers are not compatible rollback targets for schema-3 drafts; future-schema snapshots are rejected rather than rewritten.

Restore through normal Splunk administration, inspect uncertain writes before repeating them and never replay inference as part of recovery. Trash/version history help with app-level mistakes but do not replace platform backups.

## Maintainer changes

Keep provider adapters, compatibility rules, query guards, native editing and draft migrations modular. Schema changes need explicit sequential migrations, unknown-property preservation, future-version refusal and qualified rollback instructions. Changes to authority or vendor resolution require renewed security checks.

See [architecture](architecture.md), [development](development.md) and the preserved [versioned upgrade contracts](reference/upgrade-contracts.md) for detailed module-level invariants.

**Next:** [Installation](installation.md) · [Troubleshooting](troubleshooting.md) · [Release evidence](validation.md)
