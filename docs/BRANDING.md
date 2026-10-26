# Nebulah Link branding

The app uses the approved Linkline B identity supplied in `Nebulah-Link-Logo-Package.zip`. The connected li, i dot, rounded n, open k, and outlined NEBULAH lettering are retained exactly. Basic is an edition label outside the artwork.

Archive SHA-256: `5c33fdf1edf3cc6e66460464aa16f7a6ad62711a4fdb5d4c7c0f45cffb7dfdfe`.

## Included files

- `dist/brand/logo-horizontal-dark.svg`: the app header on its dark surface.
- `dist/brand/logo-dark.svg` and `logo-color.svg`: primary marks for dark and light documentation surfaces.
- `dist/brand/favicon.svg`, `favicon.ico`, and `apple-touch-icon.png`: supplied browser/device icons.
- `dist/brand/icon-192.png`: the local Discord presence preview.

These are unchanged exports from the supplied package, not reconstructed lettering. Keep their aspect ratios, connected li, original spacing, and clear space. Do not recolor or distort the logo when changing the workspace accent. The default interface accent is the supplied soft blue `#74B5D6`; a saved user accent changes controls, not the artwork.

The bridge explicitly allowlists the runtime assets. No generic public directory or arbitrary-file serving route was introduced. Original font/rebuild/print assets are not needed by the browser runtime and are not copied here.

## Interface palette

The shell uses the package palette: deep `#172C3A` for the page and inset controls, slate `#425565` for boundaries, cloud `#F5F8FA` for primary text, and sky `#74B5D6` for the default accent. Panels use `#243847`, a rounded 70% deep / 30% slate blend. Muted text mixes cloud with slate. Accent-text contrast is calculated against the actual panel color; saved user accent preferences remain intact.
