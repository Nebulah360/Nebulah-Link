# Nebulah Link Basic instructions

Read [repository policy](docs/REPOSITORY_POLICY.md) before changing or publishing.

- Public writes are limited to Jaden's approved scope: uploads, inspected title launches, power, and bounded controller input. The current extracted build remains read-only until these features are implemented and verified.
- All RTE/RTM source and every other console-write implementation belong only in private Nebulah-Link-Pro.
- Preserve independent HTTP, bridge and adapter allowlists. Unknown actions fail closed before console access.
- No notification/plugin/memory/profile/stat write code, hidden handlers, paid UI, offsets, recipes or binary modules may ship here. Approved Basic writes need explicit action and their existing safety gates.
- Local saved settings, favorites, profiles, cache, downloads and untrusted candidates are allowed; they must never mutate console state.
- Preserve private-read consent, no-key logging/storage, read-before-write/recovery safety, measured-byte verification, and proprietary-free distribution.
- Never mirror private Git history into public.
- Run python -m unittest discover -s tests -v, node --check dist/app.js, and python -m compileall -q bridge tools.
- Host checks do not establish Windows/Xbox acceptance. Keep this extracted edition labeled a migration candidate until those checks pass.

