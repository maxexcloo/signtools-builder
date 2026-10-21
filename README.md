# SignTools Builder

GitHub Actions worker for [SignTools](https://github.com/SignTools/SignTools).
It downloads a pinned revision of the upstream signer, reaches the SignTools
server over Tailscale, signs the queued app and uploads the result.

## Signing

Start signing from the SignTools web interface. It queues the job and dispatches
the **Sign** workflow. Starting or rerunning the workflow directly does not create
a signing job.

The workflow uses an Intel macOS runner because of the upstream injection
helper. It masks downloaded credentials, suppresses signer output, turns off
Fastlane telemetry and update checks, and keeps signing files out of caches and
artefacts. Review signing results in SignTools.

## Secrets

Configure these repository secrets through credential tools:

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
reuse the saved session until Apple expires it, and the next sign-in refreshes the
secret. Only the session-saving step gets the storage token. The saved session
stays a private repository secret even if the repository is public. Tailscale
runs in quiet mode, and connection failures use a generic message. A separate
workflow deletes each Sign run's logs after it completes, including failed and
cancelled runs. Actions logs are public while a run is active and until cleanup
finishes; action failures can still emit diagnostics during that window. If
cleanup fails, its workflow must be rerun or the Sign logs deleted manually.

## Development

Install [Mise](https://mise.jdx.dev) and the
[shared configuration](https://github.com/maxexcloo/dotfiles#shared-tools--tasks),
then run `mise run check`.

Pull requests run the **Check** workflow without signing credentials. The signer
wrapper fails if the upstream credential reader it expects changes, so upstream
revision updates need review.
