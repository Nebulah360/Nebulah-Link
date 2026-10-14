# Nebulah Link repository and release boundaries

Effective 2026-10-14. Basic is public source and read-only. A $5 one-time purchase will authorize a Pro download through the website. Code entry in Basic will authorize that download only; it will not turn Basic into Pro.

| Repository | Visibility | Role |
| --- | --- | --- |
| Nebulah-Web-App-main | Local core | Existing development workspace; preserve its work and history. |
| Nebulah-Link | Public | Read-only companion and download entry point when licensing is ready. |
| Nebulah-Link-Pro | Private | Basic features plus console writes and RTE/RTM. |
| Nebulah-Web-App-Legacy | Private | Archive of the former public repository and its history. |

The separate Nebulah-Web-App-Private remote is not an automatically synchronized copy of Main. Never publish its history or Pro implementation into Basic.

## Feature boundary

Basic may read console status, telemetry, storage, files, library metadata, related game content, title-update headers, and local diagnostic state. It must reject console writes at the HTTP, bridge, and adapter boundaries. Its local favorites, settings, and saved library may still change on the PC.

Pro owns uploads, inspected title launches, power, bounded controller input, notifications, file changes, DashLaunch, plugin install/load/unload/force release, RTE/RTM, profile/stat edits, and memory writes. Existing safety and beta gates remain in force. Plugin install and direct unload are not yet proven available on hardware. A purchase or license must never bypass a recovery hold, confirmation, read-back check, rollback, or capability check.

Private console data keeps explicit consent, temporary display, and no-log/no-storage rules. CPU-key display requires fresh confirmation for each read. Phone sessions may read allowlisted status and recovery state only; they cannot request private console data or writes.

## Payment and distribution

Website checkout and license issuance are not implemented. Stripe is a candidate, not a selected dependency. Until the website provides a verified redemption and download endpoint, Basic must not display a working code-entry control or claim that payment is available. A code entered into public source cannot protect Pro code. The website must validate one-time purchase and deliver only a reviewed Pro build; neither edition may embed a signing secret.

Pro is intended to ship as one Windows executable. A bundled executable is not strong obfuscation; source extraction and local patching remain possible. Keep proprietary SDK files, console binaries, keys, and local data outside the package. Sign distributable bytes when a signing identity is available and publish their SHA-256.

## Release gate

Release each edition only after relevant host tests, Windows/browser checks, real-console smoke tests, and exact artifact review. Structural XEX checks do not prove authenticity or console compatibility. Use only tracked source assets in packages; exclude `.local`, backups, tests, secrets, and console binaries. Do not claim a stable release from repository or packaging checks alone.
