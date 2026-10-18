# AGENTS.md

## Secrets

- Mask every downloaded credential before the upstream signer can log it.
- Give `SESSION_STORAGE_TOKEN` only to the session-saving step.
- Keep secrets out of `check.yaml` and keep the `pull_request` trigger off the
  Sign workflow.
- Never cache or upload signing files as artefacts.

## Structure

- Run Sign only through SignTools dispatch on an Intel macOS runner; the
  upstream injection helper requires it.
- Keep custom code in `.github/scripts/`.
- Execute upstream SignTools-CI only at the pinned commit. When bumping it or the
  Fastlane version, re-review upstream credential reads and error formatting.
- Keep the signer patch failing on any upstream mismatch.

## Verification

- Run `mise run check`.
- Live verification requires a signing job started from the SignTools web
  interface.
