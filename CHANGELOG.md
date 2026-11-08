# Changelog

One line per version. The newest version is at the top.

- **0.5.1** (2026-11-08):
  - WarlockKit 0.2.0 now runs on **HarleyLib** (new folder, install it too): the same Forever client fixes as Harley's other kits, `/wk status` self-test window, settings migrate automatically, commands refuse to run in combat. Fixed `/wk test` erroring on the alerts check when you had no pet.
  - `install.ps1` backs up the old addon folders to `_forever_\AddOn-backups` before replacing them.
  - Checks run on every push and pull request (guide validator + Lua syntax). Bethink's duplicate `tools/` folder was removed; `tools/` is the only copy.
- **0.5.0** (2026-11-07):
  - **Warlock layer:**
    - Succubus and Incubus quests at 20, an optional Felhunter chain at 30, and a check of the Felsteed quest at 40.
    - Affliction talent lines for every chapter.
    - Rotation, Soul Shard and safety tips.
    - Gold notes on training stops.
    - Need-roll lines for SFK, BFD, Gnomeregan, RFK, SM and Razorfen Downs.
    - A "join at 20" note in 20-21 Ashenvale.
  - **Tooling and help:**
    - New WarlockKit addon.
    - A training-coverage check in `tools/validate.py`.
    - AGENTS.md plus a docs folder for AI tools.
    - An issue template, an installer and a release zip.
- **0.4.0** (2026-11-07): Darkshore and Ashenvale for 16-21, a shorter Westfall, and a single Defias/Deadmines trip.
- **0.3.0** (2026-11-07): Faster travel (mage teleports, a shorter Desolace trip), optional Redridge group quests, and extra quests on the way.
- **0.2.0** (2026-11-07): First public version. Covers every Alliance race and class from 1 to 42, then hands off to Bethink for 42-60.
