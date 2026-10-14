# Nebulah Link Basic

Nebulah Link brings your Xbox 360 into a browser on your Windows PC. It connects through your installed Xbox 360 Neighborhood. A phone on the same trusted network can view live console status through the PC.

This is an early-access build. Console compatibility has been checked on a limited setup; more hardware testing is needed before a stable release.

## Start on Windows

1. Install Xbox 360 Neighborhood and confirm it can connect to your console.
2. Download this repository as a ZIP and extract the **whole** folder.
3. Double-click **Start Nebulah Link.cmd**. The launcher needs Python 3.10 or newer; it can offer to install Python through WinGet if needed.
4. Keep the bridge window open. In the browser, connect using Neighborhood's default console or enter your console's private IP address.

Nebulah Link does not include Xbox SDK files, console binaries, or games.

## What Basic can do

- Show console status, the current title, temperatures, modules, and screen captures on the PC.
- Discover storage roots, browse folders, check capacity and health, and download individual files up to 128 MiB on the PC.
- Inspect XEX metadata and compare saved file hashes. A matching hash does not prove that an XEX is safe or compatible.
- Scan a local game library, save favorites, and inspect related content and title update structure.
- Save app settings and library data on the PC.

Basic does not change console files, settings, profiles, or game memory. Nebulah Link Pro is a separate product for console controls.

## View status on your phone

Use the LAN address printed by the bridge, then enter the Phone PIN shown in the PC browser. The phone view is limited to status. Console files and private console information are accessible only from the bridge PC. If Windows Firewall blocks the phone, run **Allow Phone Through Firewall.cmd** on the PC.

The local phone connection uses unencrypted HTTP. Use a trusted private network and do not forward the bridge port to the internet.

## Keep your data when updating

The `.local` folder beside the launcher holds saved settings and library data. Keep that folder when replacing the app files with a newer version.

For help, include the displayed support code and what you were doing. Do not share private console information.

[Website](https://nebulah.app/) · [Discord](https://discord.gg/QCQcXaz6RU) · [Report an issue](https://github.com/Nebulah360/Nebulah-Link/issues)
