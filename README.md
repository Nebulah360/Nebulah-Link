# Nebulah Link Basic

Nebulah Link brings your Xbox 360 into a browser on your Windows PC. It connects through your installed Xbox 360 Neighborhood. A phone on the same trusted network can view live console status through the PC.

This is an early-access build. Console compatibility has been checked on a limited setup; more hardware testing is needed before a stable release.

## Start on Windows

1. Install Xbox 360 Neighborhood and confirm it can connect to your console.
2. Download the packaged Basic release ZIP and extract the **whole** folder. A source checkout needs the USB engine build step below.
3. Double-click **Start Nebulah Link.cmd**. The launcher needs Python 3.10 or newer; it can offer to install Python through WinGet if needed.
4. Keep the bridge window open. In the browser, connect using Neighborhood's default console or enter your console's private IP address.

Nebulah Link does not include Xbox SDK files, console binaries, or games.

## What Basic can do

Basic covers work a stranger could do with an upstream tool plus Xbox 360 Neighborhood. Game Editors and Title editors stay in Nebulah Link Pro.

- Connect, status, the current title, temperatures, and loaded modules.
- Storage browse and download, capacity, and health. Individual file downloads remain capped at 128 MiB.
- A PC FTP proxy for Neighborhood-class file access, plus file upload and folder transfer, with the same safety caps as other bridge transfers.
- Inspected title launch.
- Power warm reboot, cold reboot, and shutdown.
- Screen capture.
- Bounded controller digital pulses through Companion. Guide, analog, and hold stay off. Companion is a capability module for pulses and managed plugin load, not an editor.
- Generic plugin load. Direct unload and force-release stay paused until a console trial passes. Plugin install is not available.
- DashLaunch `launch.ini` discover, session switch, and plugin-slot save with confirmation and read-back.
- Console XNotify.
- Library scan, favorites, shortcuts, and add-on listing.
- Title-update header inspect only.
- Content placement preview.
- IGDB Discover.
- Discord presence.
- BadBuilder USB from the PC-only USB Builder tab. The selected physical USB disk is erased only after exact disk confirmation and Windows elevation.
- Local ISO header inspect.
- Theme and launcher settings on the PC.
- Phone status view.
- CPU-key reveal with consent. Each read needs fresh confirmation.
- Hash and baseline check. A matching hash does not prove that a file is safe or compatible, and this check is not an editor recipe.
- Profile package inspect (read only).
- Cherry, the PC-local virtual profile.

Game Editors and Title editors stay in Nebulah Link Pro. That includes the Nebulah Editors XEX, in-title menus, bridge RTE hubs, editor recipes, profile-write apply, and gamertag or identity writes.

The current Stream360 stack is not shipped. It needs a Nebulah rewrite before any edition ships it. This page does not classify that code as Basic or Pro.

## USB Builder on Windows

The USB Builder uses BadBuilder v2.1.0 under its BSD 3-Clause license. Its source and license are in `vendor/BadBuilder`. The packaged Basic release includes the compiled engine in `.local/badbuilder`. If using a source checkout instead, run `powershell -ExecutionPolicy Bypass -File tools/build_badbuilder.ps1` once with the .NET 10 SDK installed. Open the USB Builder tab to choose a currently connected USB disk, review the options, and type its exact `ERASE DISK N` confirmation. Downloads and extraction complete before formatting begins. The elevated engine rechecks disk identity and safety before any erase. No physical USB format/install has been hardware-tested through this Basic web route yet.

## Read from Linux or macOS

Install Python 3.10 or newer and run `bash start-local.sh` from this folder. Enter the console's private IP under **Connect console**, or save it as the default in **Settings**. Direct XBDM on TCP port 730 provides live status, storage browsing, file download and upload, inspected launch, power, notify, and PC screen capture. Plugin load, controller pulses, and launch.ini still need Windows Neighborhood. The Linux path has been checked for the earlier read operations only. One Ubuntu VM connected through direct XBDM, discovered ten roots, browsed 74 HDD entries, refreshed status, and captured a screen. More Linux hardware setups remain to be tested.

## View status on your phone

Use the LAN address printed by the bridge, then enter the Phone PIN shown in the PC browser. The phone view is limited to status. Console files and private console information are accessible only from the bridge PC. If Windows Firewall blocks the phone, run **Allow Phone Through Firewall.cmd** on the PC.

The local phone connection uses unencrypted HTTP. Use a trusted private network and do not forward the bridge port to the internet.

If you already have a PEM certificate and key trusted by your clients, start with `--tls-cert <certificate.pem> --tls-key <private-key.pem>` for optional HTTPS on both PC and phone URLs. Keep the private key outside this repository. Physical-phone HTTPS testing remains open.

## Keep your data when updating

The `.local` folder beside the launcher holds saved settings and library data. Keep that folder when replacing the app files with a newer version.

For a new folder, stop both copies of Basic. Run `python tools/migrate-local.py <old-basic-folder> <new-basic-folder>` to preview, then add `--apply` to copy only missing saved files. Existing destination files stay in place. Keep the old folder for rollback; do not use this between Basic and Pro.

For help, include the displayed support code and what you were doing. Do not share private console information.

[Website](https://nebulah.app/) · [Discord](https://discord.gg/QCQcXaz6RU) · [Report an issue](https://github.com/Nebulah360/Nebulah-Link/issues)
