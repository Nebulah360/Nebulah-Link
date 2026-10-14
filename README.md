# Nebulah Link — Basic

Local Xbox 360 companion for your Windows PC or phone. The Windows bridge connects through Xbox 360 Neighborhood; your phone uses that PC on your private network.

**Migration candidate:** 44 host tests, JavaScript syntax checks, and Python compilation checks pass. Windows/Xbox hardware acceptance of this extracted edition remains pending.

## Get started

1. Install Xbox 360 Neighborhood and confirm it connects to your console.
2. Download and extract the complete project, then run **Start Nebulah Link.cmd** on Windows.
3. Connect to Neighborhood's default console or enter a private console IP.

For phone access, open the LAN URL printed by the bridge and enter the Phone PIN displayed on the PC. Keep the bridge window open. HTTP is unencrypted; use a trusted private network and never forward the bridge port.

## Current Basic features

- Console status, current title, temperatures, screen capture, and module inventory.
- Discovered storage roots, folder browsing, capacity/health reads, and individual file downloads up to 128 MiB.
- XEX metadata, SHA-256 checks, and untrusted baseline proposals with title and provenance.
- Local library scanning, favorites, saved profiles, cached metadata, and existing launch history.
- Local settings and accent color. Read API routes also retain title-update inspection, optional metadata lookup, and Discord activity support.

The current extracted build is read-only. The approved Basic write scope is file uploads, inspected title launches, power commands, and bounded controller input. These still need implementation and hardware verification. Unknown console actions are rejected at the HTTP, bridge, and adapter boundaries; no setting enables unimplemented writes.

## Pro boundary

Nebulah Link Pro is private and includes the Basic feature set plus full RTE/RTM and other console writes, including profile/stat edits, plugin and DashLaunch changes, and memory writes. These implementations stay out of Basic. Pro is still a prior core snapshot; parity with the latest uncommitted Main work remains pending. Payment enforcement is not implemented yet.

Keep `.local` when updating; it contains your saved settings and library. XEX structure and digest checks do not prove safety, authenticity, or console compatibility. No games, console binaries, or proprietary SDK files are included.

## Development

Run `python -m unittest discover -s tests -v`, `node --check dist/app.js`, and `python -m compileall -q bridge tools`.

Read [repository policy](docs/REPOSITORY_POLICY.md) and [agent instructions](AGENTS.md) before changing or releasing this project.

[Website](https://nebulah.app/) · [Discord](https://discord.gg/QCQcXaz6RU) · [Issues](https://github.com/Nebulah360/Nebulah-Link/issues)
