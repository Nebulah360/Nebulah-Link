# Nebulah Link branding

The app uses the approved Linkline B identity supplied in `Nebulah-Link-Logo-Package.zip`. The connected li, i dot, rounded n, open k, and outlined NEBULAH lettering are retained exactly. Basic is an edition label outside the artwork.

Archive SHA-256: `5c33fdf1edf3cc6e66460464aa16f7a6ad62711a4fdb5d4c7c0f45cffb7dfdfe`.

## Included files

- `dist/brand/symbol-color.svg`, `symbol-white.svg`, and `symbol-dark.svg`: the N mark. The app header starts with this symbol and expands into the Nebulah Link name. Do not redraw it.
- `dist/brand/favicon.svg`, `favicon.ico`, and `apple-touch-icon.png`: the same N for the browser and home screen.
- `dist/brand/icon-192.png`: the Discord presence preview and the file to upload as `nebulah_n`.
- `dist/brand/logo-horizontal-dark.svg`, `logo-dark.svg`, and `logo-color.svg`: full lockups for places that need the name inside the artwork. The running app does not use them in place of the N.

These are unchanged exports from the supplied package, not reconstructed lettering. Keep their aspect ratios, connected li, original spacing, and clear space. Do not recolor or distort the logo when changing the workspace accent. The default interface accent is the supplied soft blue `#74B5D6`; a saved user accent changes controls, not the artwork.

The bridge explicitly allowlists the runtime assets. No generic public directory or arbitrary-file serving route was introduced. Original font/rebuild/print assets are not needed by the browser runtime and are not copied here.

## Interface palette

The shell uses the package palette: deep `#172C3A` for the page and inset controls, slate `#425565` for boundaries, cloud `#F5F8FA` for primary text, and sky `#74B5D6` for the default accent. Panels use `#243847`, a rounded 70% deep / 30% slate blend. Muted text mixes cloud with slate. Accent-text contrast is calculated against the actual panel color; saved user accent preferences remain intact.
