# SignTools Builder

GitHub Actions worker for [SignTools](https://github.com/SignTools/SignTools).
It downloads a pinned revision of the upstream signer, reaches the SignTools
server over Tailscale, signs the queued app and uploads the result.

## Signing

Start signing from the SignTools web interface. It queues the job and dispatches
the **Sign** workflow. Starting or rerunning the workflow directly does not create
a signing job.

The workflow uses an Intel macOS runner because of the upstream injection
helper. It suppresses signer output and turns off Fastlane telemetry and update
checks. Review signing results in SignTools.

## Secrets

Set these repository secrets; the workflow maintains `FASTLANE_SESSION` itself:

| Secret                  | Purpose                                                |
| ----------------------- | ------------------------------------------------------ |
| `FASTLANE_SESSION`      | Apple session saved automatically after authentication |
| `SECRET_KEY`            | Builder authentication key set by SignTools            |
| `SECRET_URL`            | Server URL set by SignTools                            |
| `SESSION_STORAGE_TOKEN` | Repository-scoped token with Secrets read/write access |
| `TS_AUDIENCE`           | Tailscale federated identity audience                  |
| `TS_OAUTH_CLIENT_ID`    | Tailscale federated identity client ID                 |

The Tailscale identity must authorise this repository's `main` branch and
`tag:ephemeral`, with access to the private SignTools server.

The first signing request needs Apple 2FA through SignTools. Later requests
reuse the saved session until Apple expires it.

Each Sign run's logs are deleted when it completes. If that cleanup fails, rerun
the **Remove Signing Logs** workflow.

## Development

Install [Mise](https://mise.jdx.dev) and the
[shared configuration](https://github.com/maxexcloo/dotfiles#shared-tools--tasks),
then run `mise run check`.
