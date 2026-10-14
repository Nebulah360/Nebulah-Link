# Nebulah Link — Basic

Local Xbox 360 companion for your Windows PC or phone. The Windows bridge connects through Xbox 360 Neighborhood; your phone uses that PC on your private network.

**Migration candidate:** Host tests, JavaScript syntax checks, and Python compilation checks pass. Windows/Xbox hardware acceptance of this extracted edition remains pending. This public repository receives reviewed Basic snapshots; day-to-day development and hardware trials stay in local/private workspaces.

## Get started

1. Install Xbox 360 Neighborhood and confirm it connects to your console.
2. Download and extract the complete project, then run **Start Nebulah Link.cmd** on Windows.
3. Connect to Neighborhood's default console or enter a private console IP.

For phone access, open the LAN URL printed by the bridge and enter the Phone PIN displayed on the PC. Phone access shows status only; console files and private data stay on the bridge PC. Keep the bridge window open. HTTP is unencrypted; use a trusted private network and never forward the bridge port.

## Current Basic features

- Console status, current title, temperatures, screen capture, and module inventory.
- Discovered storage roots, folder browsing, capacity/health reads, and individual file downloads up to 128 MiB.
- XEX metadata, SHA-256 checks, and untrusted baseline proposals with title and provenance.
- Local library scanning, favorites, saved profiles, cached metadata, and existing launch history.
- Storage health and exact-hash comparison of saved XEX observations.
- Per-game related-content discovery and structural title-update inspection.
- Local settings and accent color. Read API routes also retain optional metadata lookup and Discord activity support.

Basic is read-only. Unknown console writes are rejected at the HTTP, bridge, and adapter boundaries. Local favorites, library records, and settings remain editable on the PC.

## Pro boundary

Nebulah Link Pro is private and owns console writes, including uploads, inspected launches, power, controller input, notifications, DashLaunch, plugins, RTE/RTM, and profile/stat edits. The planned $5 one-time purchase will authorize a Pro download from the website; code entry in Basic will not unlock writes here. Checkout and license issuance are not implemented yet. Pro is still a prior core snapshot; parity with the latest uncommitted Main work remains pending.

Keep `.local` when updating; it contains your saved settings and library. XEX structure and digest checks do not prove safety, authenticity, or console compatibility. No games, console binaries, or proprietary SDK files are included.

## Development

Run `python -m unittest discover -s tests -v`, `node --check dist/app.js`, and `python -m compileall -q bridge tools`.

After hardware review, `tools/package-beta.ps1` creates a source ZIP from the exact committed Git bytes and prints its SHA-256. `-Preview` creates a local candidate from the current commit. Neither command publishes a release.

Read [repository policy](docs/REPOSITORY_POLICY.md) and [agent instructions](AGENTS.md) before changing or releasing this project.

[Website](https://nebulah.app/) · [Discord](https://discord.gg/QCQcXaz6RU) · [Issues](https://github.com/Nebulah360/Nebulah-Link/issues)
