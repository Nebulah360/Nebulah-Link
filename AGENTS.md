# Nebulah Link free-edition instructions

Read [repository policy](docs/REPOSITORY_POLICY.md) before changing or publishing.

- Public default: read-only console access. Public writes require Jaden's explicit scoped exception.
- All RTE/RTM source and all console-write implementation belong only in private Nebulah-Link-Pro. Reads remain free; console writes use the planned one-time paid entitlement.
- Preserve independent HTTP, bridge and adapter allowlists. Unknown actions fail closed before console access.
- No launch/upload/power/controller/notification/plugin/memory write code, hidden handlers, paid UI, offsets, recipes or binary modules may ship here.
- Local saved settings, favorites, profiles, cache, downloads and untrusted candidates are allowed; they must never mutate console state.
- Preserve private-read consent, no-key logging/storage, read-before-write/recovery safety in Pro, measured-byte verification, and proprietary-free distribution.
- Keep free development private until the clean public source is reviewed. Never mirror private Git history into public.
- Run python -m unittest discover -s tests -v, node --check dist/app.js, and python -m compileall -q bridge tools.
- Host checks do not establish Windows/Xbox acceptance. Keep this extracted edition labeled a migration candidate until those checks pass.

