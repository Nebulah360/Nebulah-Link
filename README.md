# Nebulah Link — Free

Read-only Xbox 360 companion for your Windows PC or phone. The local Windows bridge connects through Xbox 360 Neighborhood; your phone uses that PC on your private network.

**Migration candidate:** 44 host tests, JavaScript syntax checks, and Python compilation checks pass. Windows/Xbox hardware acceptance of this extracted edition remains pending.

## Get started

1. Install Xbox 360 Neighborhood and confirm it connects to your console.
2. Download and extract the complete project, then run **Start Nebulah Link.cmd** on Windows.
3. Connect to Neighborhood's default console or enter a private console IP.

For phone access, open the LAN URL printed by the bridge and enter the Phone PIN displayed on the PC. Keep the bridge window open. HTTP is unencrypted; use a trusted private network and never forward the bridge port.

## Free features

- Console status, current title, temperatures, screen capture, and module inventory.
- Discovered storage roots, folder browsing, capacity/health reads, and individual file downloads up to 128 MiB.
- XEX metadata, SHA-256 checks, and untrusted baseline proposals with title and provenance.
- Local library scanning, favorites, saved profiles, cached metadata, and existing launch history.
- Local settings and accent color. Read API routes also retain title-update inspection, optional metadata lookup, and Discord activity support.

This edition has no title launches, uploads, console power controls, notifications, controller input, plugin changes, or memory/stat editing. Unknown console actions are rejected at the HTTP, bridge, and adapter boundaries. No local setting or Admin switch can enable writes.

## Private features

All RTE/RTM source stays private, including read-only RTE/RTM implementation. Read features remain free through a separately distributed private-source component; that integration is not yet shipped in this extracted edition. Console writes belong to Nebulah Link Pro with a planned one-time paid entitlement. Payment enforcement is not implemented yet.

Keep `.local` when updating; it contains your saved settings and library. XEX structure and digest checks do not prove safety, authenticity, or console compatibility. No games, console binaries, or proprietary SDK files are included.

## Development

Run `python -m unittest discover -s tests -v`, `node --check dist/app.js`, and `python -m compileall -q bridge tools`.

Read [repository policy](docs/REPOSITORY_POLICY.md) and [agent instructions](AGENTS.md) before changing or releasing this project.

[Website](https://nebulah.app/) · [Discord](https://discord.gg/QCQcXaz6RU) · [Issues](https://github.com/Nebulah360/Nebulah-Web-App/issues)
