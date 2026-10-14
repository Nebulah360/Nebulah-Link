# Nebulah Link repository and release boundaries

Effective 2026-10-14. Jaden approved the Basic write scope: uploads, launches, power, and controller input.

| Repository | Visibility | Role |
| --- | --- | --- |
| Nebulah-Web-App-main | Local core | Existing development workspace; leave its work and history in place. |
| Nebulah-Link | Public | Basic companion with the limited write scope below. |
| Nebulah-Link-Pro | Private | Basic features plus the full core, RTE/RTM, and other console writes. |
| Nebulah-Web-App-Legacy | Private | Archive of the former public repository and its history. |

The separate Nebulah-Web-App-Private remote still exists. Do not treat it as an automatically synchronized copy of Main or publish its history to Basic.

## Feature boundary

Basic may read console status, telemetry, storage, files, and metadata. Its only approved console writes are explicit file uploads, inspected title launches, power commands, and bounded controller input. This is a scope decision, not a claim that the extracted Basic build implements those writes today.

For Basic uploads, require an explicit destination, size limits, no silent overwrite, and remote read-back verification. For launches, use a fresh server-inspected XEX and a short-lived single-use ticket; reject DLLs and plugins through the title-launch route. Power and controller actions require an authenticated, explicit user action; bound controller input so it cannot remain held indefinitely. Discover storage roots instead of assuming a drive letter.

Pro contains Basic features and owns RTE/RTM, profile and game/stat editing, memory writes, notifications, file rename/delete, DashLaunch and plugin changes, and any other console-write implementation. Keep Pro source, tests, UI, offsets, recipes, and binaries out of Basic. Do not use a Basic setting or payment switch to bypass an unavailable capability.

Private console data keeps its explicit-consent, temporary-display, and no-log/no-storage rules. CPU-key display requires fresh confirmation for each read. Phone routes cannot retrieve private console data.

## Release gate

Release each edition as a polished project only after its implemented features pass relevant host tests, Windows/browser checks, and real-console smoke tests. Review exact package bytes and hardware evidence; structural XEX checks alone do not prove authenticity or compatibility. Keep recovery holds, read-back checks, and rollback for writes. Never ship demo controls or simulated console results in production.

Basic currently remains an extracted read-only migration candidate; its approved write categories still need implementation and hardware acceptance. Pro is a prior core snapshot and has not yet incorporated all uncommitted work in Main. Neither edition gains a stable-release claim from this policy change. Pricing, billing, and entitlement enforcement are not implemented.
