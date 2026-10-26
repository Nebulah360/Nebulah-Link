# Nebulah Link repository and release boundaries

Updated 2026-10-26. Basic is the public source edition. Pro accounts and protected tester downloads are managed through the product website; checkout remains disabled. Basic contains no Pro code-entry or local unlock control.

| Repository | Visibility | Role |
| --- | --- | --- |
| Nebulah-Web-App-main | Local core | Existing development workspace; preserve its work and history. |
| Nebulah-Link | Public | Public Basic companion and download entry point when licensing is ready. |
| Nebulah-Link-Pro | Private | Basic Link features plus Game Editors and Title editors. |
| Nebulah-Web-App-Legacy | Private | Archive of the former public repository and its history. |

The separate Nebulah-Web-App-Private remote is not an automatically synchronized copy of Main. Never publish its history or Pro implementation into Basic.

## Feature boundary

The edition split is locked. If a stranger could do the same job with an upstream tool plus Xbox 360 Neighborhood, the feature is Basic. If they need Nebulah Game Editors or Title editors, the feature is Pro.

### Basic

Basic includes:

- Connect, status, temperatures, and module lists.
- Storage browse, download, capacity, and health.
- A PC FTP proxy in the Neighborhood class.
- File upload and folder transfer.
- Inspected title launch.
- Power warm, cold, and shutdown.
- Screen capture.
- Bounded controller bind and digital pulses.
- Generic plugin load, unload, install, and force-release. Plugin install and direct unload are not yet proven available on hardware.
- DashLaunch `launch.ini` switch and plugin slots.
- Console XNotify.
- Library scan, favorites, shortcuts, and add-on listing.
- Title-update header inspect only.
- Content placement preview.
- IGDB Discover.
- Discord presence.
- BadBuilder USB. BadBuilder may format a locally attached PC USB disk only after exact disk confirmation and Windows elevation.
- Local ISO header inspect.
- Theme and launcher settings.
- Phone status view.
- CPU-key reveal with consent. Each read needs fresh confirmation. Private console data keeps explicit consent, temporary display, and no-log/no-storage rules.
- Hash and baseline check. This check is not an editor recipe.
- Profile package inspect (read only).
- Cherry, the PC-local virtual profile.
- LinkUI status and deep-link presence.
- The Companion protocol (pulses and managed plugin load) as a capability module, not an editor.

Basic favorites, settings, and the saved library may still change on the PC. Phone sessions may show allowlisted status and recovery state only. They cannot request private console data beyond that allowlist.

Existing safety and beta gates remain in force. A purchase or license must never bypass a recovery hold, confirmation, read-back check, rollback, or capability check.

### Pro only

Pro is Basic plus Game Editors and Title editors. Pro-only work is:

- The Nebulah Editors XEX and in-title menus.
- Bridge RTE hubs for BO1, BO2, COD4, WaW, MW2, MW3, and Ghosts.
- RTE apply and poke, and unlock, prestige, and stat recipes.
- `iw_cbuf`, SV command, and client-table edits used by those hubs.
- Editors command trace.
- The Xenia module hash used to pin editor builds.
- Profile vibration and profile-write apply.
- Gamertag, identity, and pregame name writes.
- Host-client and off-host identity patches.
- Any UI for edit stats, unlock all, force host, FOV, or godmode.

### Deferred (not decided)

These items stay open. This policy does not classify them as Basic or Pro:

- LinkUI cover push to the console.
- Live preflight and local packet.
- The `experimental_core` transfer lab.
- Title-update install and activate. Header inspect stays Basic.
- Generic memory peek without a recipe.
- The current Stream360 stack. It needs a Nebulah rewrite before any edition ships it. Do not classify the current code as a Basic or Pro product.

## Payment and distribution

LinkUI status and deep-link presence are Basic. Basic LinkUI sources that implement only those surfaces may live in the public Basic repository. Nebulah Editors, Title editors, editor recipes, and editor write UI stay in the private Pro repository. LinkUI cover push to the console is deferred and is not classified here. Basic remains free for public trials. LinkUI development and testing do not imply account authentication, payment gating, or entitlement enforcement in the local app.

Pro access and protected downloads are managed on https://link.nebulah.app/link-pro using Nebulah accounts. Checkout remains disabled. This public Basic app has no Pro code-entry or local unlock control. A code entered into public source cannot protect Pro code; only the website may validate entitlements and deliver the reviewed Pro artifact. Neither edition may embed a signing secret.

Pro is intended to ship as one Windows executable. A bundled executable is not strong obfuscation; source extraction and local patching remain possible. Keep proprietary SDK files, console binaries, keys, and local data outside the package. Sign distributable bytes when a signing identity is available and publish their SHA-256.

## Release gate

October 26 source status: the public app is Basic, with no embedded Pro implementation. The separate website provides existing entitled accounts with the reviewed Pro tester; billing remains disabled. Source availability and a successful hosted demo are not Windows/Xbox, USB, or physical-phone acceptance. The hardware and release gates below remain in force.

Release each edition only after relevant host tests, Windows/browser checks, real-console smoke tests, and exact artifact review. Structural XEX checks do not prove authenticity or console compatibility. Use only tracked source assets in packages; exclude `.local`, backups, tests, secrets, and console binaries. Do not claim a stable release from repository or packaging checks alone.


## Curated publication workflow

Use the former Legacy publication model recorded in public commit `679377c5de1e03a658e20d8fff0e3f8c8a37726c`: develop and test in local/private workspaces, then promote a reviewed public snapshot. Legacy remains a private preservation archive; never copy its mixed-feature history.

Review the exact diff against the last public commit and the provenance of all imported assets. Run applicable host, browser, and boundary tests. For presentation-only changes, document that adapter behavior and existing hardware limits remain unchanged. Console behavior or distributable binary changes require their relevant hardware/artifact evidence before release. Never label host-only validation as hardware acceptance or stable status.

Archive committed tracked bytes, publish their SHA-256, preserve earlier commits, and keep `.local`, credentials, backups, proprietary inputs, and unreviewed binaries out of public source. Do not synchronize private Main or Pro wholesale, rewrite public history, or publish a prebuilt USB engine merely because source checks pass.
