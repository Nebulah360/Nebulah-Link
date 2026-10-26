# Basic workspace source refresh — October 26, 2026

## Provenance and scope

Base: public `Nebulah360/Nebulah-Link` commit `8846a5d27e54c7c8bdac9f0ff0a946d3f60782f6`. Work was prepared in an isolated local worktree. No dirty Basic-Dev workspace, private Pro implementation, mixed-feature Legacy history, or local console data was copied into this snapshot.

The release follows the curated publication model documented in public commit `679377c5de1e03a658e20d8fff0e3f8c8a37726c`. The later approved Neighborhood-class Basic boundary remains intact; this refresh does not restore the superseded read-only edition policy.

## User-visible changes

- The supplied Linkline logo, browser/device icons, and Discord preview replace the old generic mark.
- A compact connection overview, readable status tiles, desktop workspace navigation, and responsive mobile navigation organize the existing controls.
- A keyboard skip link and programmatic selected-tool state improve navigation. Controls retain visible focus and minimum touch sizes.
- The default and reset accent is Nebulah blue; existing saved colors remain unchanged. Button foreground and accent text continue to adapt to custom colors.
- Product/help links use `link.nebulah.app`. Source download instructions no longer imply that a signed installer or compiled USB engine is present in Git.
- Updated user documentation covers setup, task flows, safeguards, phone limits, local updates, and source validation.

## Root-cause fix

`app.js` declared a global `bytesLabel` function while `badbuilder.js` declared the same name as a global constant. The classic scripts share a global scope, so the USB script failed before attaching its controls. The duplicate declaration was removed; USB now reuses the existing app formatter, including its unknown-value handling.

The integration regression parses every script loaded by the real HTML in a shared scope. Browser checks also open the USB workspace and require both inventory and builder-availability calls, so a mounted-looking page cannot hide this failure.

## Validation and constraints

- Python tests cover the existing Basic allowlists, Cherry, content planning, FTP safeguards, and the new explicit brand-asset HTTP routes.
- Node tests cover combined script declarations, selected-tool accessibility, local asset references, and existing module measure/load behavior.
- Chromium checks run the real app scripts at 320, 390, 768, and 1440px, open all six workspaces, inspect image proportions and overflow, verify appearance persistence/reset, and confirm phone sessions cannot see PC tool panels.
- JavaScript syntax and Python compilation are checked separately.
- The new asset routes serve only explicit trusted files. Invalid Host values, path traversal, unknown assets, and local-data requests remain denied.

Browser API fixtures are test-only. The production app contains no simulated console state. No console operation, physical USB formatting, paid account operation, or physical-phone acceptance was performed. Existing limited hardware evidence and beta restrictions remain unchanged; this source refresh is not a stable binary release.
