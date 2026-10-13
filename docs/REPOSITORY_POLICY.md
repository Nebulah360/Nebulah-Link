# Nebulah Link repository and access policy

Effective 2026-10-13. Only Jaden's explicit, scoped instruction may authorize a public console-write exception.

| Repository | Visibility | Purpose |
| --- | --- | --- |
| Nebulah-Web-App-Legacy | Private | Preserve the former public repository and old commits. |
| Nebulah-Web-App | Public | Free read-only console companion with fresh history. |
| Nebulah-Web-App-Private | Private | Development and testing for the free read-only companion. |
| Nebulah-Link-Pro | Private | All RTE/RTM source and console-write implementation. |

## Feature boundary

All console reads are free: telemetry, status, browsing, downloads, file metadata/hash checks, module inventory, and read-only RTE/RTM inspection.

All RTE/RTM code stays private, including read-only implementation, tests, UI, offsets, recipes, and binary modules. Free RTE/RTM read access requires a separately distributed private-source component; this integration is not yet shipped in the extracted free edition.

Console writes belong exclusively in Pro and require the planned one-time paid entitlement: uploads, renames/deletes, launches, power controls, notifications, controller input, plugin changes, DashLaunch configuration changes, memory writes, and game/stat edits.

Local PC/browser preferences, profiles, favorites, cache, candidate JSON, downloads, and existing launch history remain free. They must never dispatch a console write. Private console reads keep their explicit-consent, temporary-display, and no-log/no-storage rules.

## Enforcement and releases

- Public code and packages contain no RTE/RTM or console-write implementation, dormant handlers, hidden controls, recipes, offsets, or binary modules.
- Reject unsupported operations at HTTP, bridge, and console adapter boundaries. No Admin mode, saved setting, or public payment switch may enable a write.
- Read routes must not call console-write helpers. Connecting must not send notifications, load modules, or clean up console files.
- Run the read-only boundary tests and relevant read-feature tests before publishing.
- Do not mirror private source or Git history into the clean public repo. Publish sanitized files with fresh history.
- Preserve the mixed implementation privately before removing it from the free development tree.
- Payment does not override hardware acceptance, consent, exact-build checks, recovery holds, or verification gates. Pricing, payment processing, license issuance, and entitlement enforcement remain unimplemented.
- Historical public copies and forks are not retracted by this migration.

## Current migration evidence

The full implementation and tests are preserved in Nebulah-Link-Pro. The extracted read-only source passes 44 host tests, JavaScript syntax checks, and Python compilation checks. It retains the local workspace format and free read APIs while omitting paid code.

Windows/Neighborhood/real-console acceptance of the extracted edition is pending. Some read features currently have API support without their former full UI; the free UI provides connection, telemetry, browsing, downloads, XEX inspection and candidate export, library scanning, favorites, profiles, inventory and screen capture.

The repository switch is complete. The former public repository is private as Nebulah-Web-App-Legacy. The new public Nebulah-Web-App was generated from the sanitized default branch with fresh history; its root commit is ee0b53d49f7269227a03ccd686f3a95282c83f5a. No old write commits were imported. Free development and Pro remain private. The extracted free edition remains a migration candidate pending Windows/Xbox acceptance.

