# Nebulah Link Basic user guide

Basic is a local console workspace. The browser talks to a bridge running on your PC; the bridge talks to your Xbox 360. The public website and sample demo do not connect to your console.

## Connect and find your files

1. On Windows, install Xbox 360 Neighborhood separately and confirm that it can reach the console.
2. Extract the entire Basic source folder and run **Start Nebulah Link.cmd**. Python 3.10 or newer is required; the launcher can offer installation through WinGet.
3. Keep the bridge window open. In **Connect your console**, leave the target blank for Neighborhood's default console or enter its name/private IP address.
4. Select **Connect**, then **Discover storage** in Storage. Choose a returned storage root; drive names differ between consoles.
5. Browse folders. Use **Inspect** before launching an XEX. DLLs and plugins are not title launches.

The current title, CPU/GPU temperature, and kernel readings stay above the workspace. Unavailable readings remain unavailable; Basic does not substitute simulated values.

## Use the workspaces

| Workspace | What to do there |
| --- | --- |
| Storage | Browse discovered drives, download files, transfer new files/folders, inspect XEX files, inspect a local ISO, and check storage health. |
| Library | Refresh saved library entries, scan for XEX files, open favorites, inspect add-on metadata, and preview content placement. |
| Discover | Search Xbox 360 titles through IGDB after configuring a Twitch application on the bridge PC. |
| Console | Use implemented console controls, inspect profile packages, inspect/load a supported generic plugin, and manage `launch.ini` with its confirmation and read-back checks. |
| USB builder | Inspect local Windows USB inventory and prepare a BadBuilder build after installing the engine. |
| Settings | Save a default console, connection profiles, launcher preferences, and optional PC-local Cherry/FTP settings. |

Select the accent-color button in the header to change appearance. New browsers start in Nebulah blue. Existing saved colors are preserved; **Reset to Nebulah blue** changes only this browser's appearance preference.

## Transfer and console safeguards

- Each file transfer remains limited to 128 MiB. Existing destination files are not silently replaced.
- Folder transfers use the same per-file limits and allow cancellation. Review the destination before starting.
- Title launch requires server inspection and a short-lived, single-use launch ticket. A file hash match does not establish safety or console compatibility.
- Power, notifications, controller pulses, plugin operations, and `launch.ini` changes keep their capability, confirmation, and recovery checks. A failed operation must not be blindly retried.
- Controller support is bounded digital pulses. Guide, analog, and hold remain unavailable.
- Generic plugin load is implemented. Direct unload and force-release remain paused for console validation; plugin install is unavailable.
- Profile package inspection is read only. Cherry modifies a PC-local virtual profile, not the Xbox profile or Xbox Live account.
- CPU-key display requires fresh confirmation for every read and clears automatically. Do not include private console information in screenshots or support reports.

Game Editors, Title Editors, editor recipes, profile/identity writes, and RTE are not included in Basic. The current Stream360 implementation is not distributed.

## Build a USB drive

The source repository includes BadBuilder v2.1.0 under its BSD 3-Clause license, not a compiled engine. Install the .NET 10 SDK, then run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_badbuilder.ps1
```

Open **USB builder**, refresh inventory, and review the selected physical disk and build options. Formatting erases that disk. Nothing is erased until you submit its exact `ERASE DISK N` confirmation and approve Windows elevation. Downloads and extraction finish before formatting; the elevated engine rechecks disk identity and safety.

No physical USB format/install acceptance is claimed for this browser route. Do not choose a disk containing data you need to retain.

## View status on a phone

Use the private LAN address printed by the bridge. On the PC, open **Phone pairing** and select **Show Phone PIN on PC**. Enter the temporary PIN on the phone. Phone sessions are limited to allowlisted status; console files, private data, and controls remain PC-only.

If Windows Firewall blocks the phone, run **Allow Phone Through Firewall.cmd** on the PC. HTTP is unencrypted: use a trusted private network and never forward the bridge port to the internet.

Optional HTTPS accepts `--tls-cert <certificate.pem> --tls-key <private-key.pem>` when your clients trust the certificate. Keep its private key outside the repository. Physical-phone HTTPS acceptance remains open.

## Linux and macOS

Run `bash start-local.sh` with Python 3.10 or newer, then enter the console's private IP. Direct XBDM uses TCP port 730. The source implements status, browsing, transfer, inspected launch, power, notify, and screenshot operations; only the earlier read workflow has recorded Linux hardware checks. Plugin load, controller pulses, and `launch.ini` still require Windows Neighborhood.

Do not interpret source availability or browser tests as hardware acceptance on these platforms.

## Update without losing local data

Stop both copies before updating. `.local` beside the launcher holds saved settings and library data. Keep it when replacing application files.

When moving to a new folder, preview the migration first:

```text
python tools/migrate-local.py <old-basic-folder> <new-basic-folder>
python tools/migrate-local.py <old-basic-folder> <new-basic-folder> --apply
```

Only missing saved files are copied; existing destination files stay in place. Keep the old folder for rollback. Do not use this migration between Basic and Pro.

## When something fails

Keep the displayed support code and the steps that led to it. Check that Neighborhood can connect and that the console is responsive before reconnecting after a recovery hold. A disconnected browser is not evidence that an operation did not happen; inspect the result before retrying.

Ask in [Discord](https://discord.gg/QCQcXaz6RU) or [report an issue](https://github.com/Nebulah360/Nebulah-Link/issues). Remove keys, pairing tokens, serials, account data, keyvaults, and proprietary files from reports.
