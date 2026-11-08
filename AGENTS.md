# AGENTS.md: instructions for AI coding tools

Read this file before you edit anything in this repo. It is written for any AI coding tool or local model: Claude Code, Cursor, ChatGPT, Ollama, LM Studio and others. The longer background is in `docs/`.

## Before you edit
1. Read the open issues with `gh issue list`. If you don't have the gh tool, open the Issues tab on GitHub. Fix what the player reported, not what you guess.
2. Read `CHANGELOG.md` to see what changed recently.
3. Run the validator once so you know the starting state (see "Check your work").

## What this repo is
This is a leveling guide for **WoW Forever**. It runs inside the game through the Guidelime addon.
- **Game version:** WoW Forever, client 1.60.1, `## Interface: 16001`. Addons are Lua 5.1 and use the Forever addon API.
- **Who it covers:** every Alliance race and class, levels 1-42. At 42 the route hands off to Bethink's guides for 42-60.
- **Licence:** GPLv3. The route text is adapted from Bethink's Guidelime guides, so keep every file GPLv3-compatible.
- **Never copy text from RestedXP guides.** RestedXP is not GPL. You may compare its routes for ideas only.

## Folder layout
| Path | What it is |
| --- | --- |
| `Guidelime_HarleyMage/` | The guide addon. `Guidelime_HarleyMage.toc` lists the chapters; `guides/*.lua` holds one chapter per file. |
| `Guidelime_Bethink/` | Bethink's 1-60 guides. The 42-60 part is used, and `AGENTS.md` inside it holds the original authoring rules. Don't edit it. |
| `WarlockKit/` | A helper addon for warlocks: shard counter, pet and stone alerts, buttons, talent helper, bar layout. |
| `tools/` | Python checkers: `validate.py`, `questie.py`, `guide_parser.py`, `xp_budget.py`, `zone.py`, `hub.py`. |
| `docs/` | Background: how the route was built, the research notes and a prompt template for AI tools. |
| `install.ps1`, `.github/workflows/release.yml` | Install the addons into the game. Pushing a `v*` tag builds the release zip. |

## Check your work (always do this)
Everything runs on plain Python 3.10 or newer. Nothing needs to be installed with pip.
```
python tools/validate.py
```
- On Windows, `py` works as well as `python`.
- A good result ends in `0 errors.` and `Training coverage 2-42: 0 warnings`.
- `tools/questie.py` needs the QuestieDB addon. Set the path to your game folder once, in the `WOW_DIR` line of `tools/config.txt` or the `FOREVER_WOW_DIR` environment variable. Then:
```
python tools/questie.py quest 1739 npc 6122 item 6912
```
- The output shows each quest's name, level, faction, previous and next quests, quest giver and turn-in NPC with coordinates, and objectives.
- An ID that doesn't exist prints `NOT FOUND`. **Never use an ID that the tool can't find.**

## Guidelime tag glossary (one screen)
A chapter is a Lua file that holds `Guidelime.registerGuide([[ ... ]], "Harley Mage")`. Each line inside the brackets is one step.
| Tag | Meaning |
| --- | --- |
| `[N 20-21 Ashenvale (Harley)]` | Chapter name. The level range comes first. |
| `[D text]` | Chapter description. |
| `[GA Alliance,Softcore]` | Who can use the whole chapter. |
| `[NX 21-22 Redridge Mountains (Harley)]` | The next chapter. It must match that chapter's `[N ...]` exactly. |
| `[A Warlock]`, `[A Priest,Mage,Warlock]`, `[A Human]` | Who sees this step (class and/or race). Guidelime hides it from everyone else. |
| `[QA1716]` / `[QC1738]` / `[QT1739]` | Accept, complete or turn in a quest. The arrow finds the NPC by itself. |
| `[QC1802,1]` | Complete only objective 1. |
| `[G39.24,84.96 Stormwind City]` | An arrow to coordinates. Use it only for travel and trainers. |
| `[L27.80,72.80 Hillsbrad Foothills]` | A map pin only, with no arrow. |
| `[T]` | Training step: learn spells at a trainer. |
| `[V]` | Vendor step: buy, repair, restock. |
| `[O]` | Optional: doesn't block the next step. |
| `[OC]` | Optional comment: a tip with no checkbox. |
| `[XP20]` | Level marker: "reach level 20". |
| `[H Astranaar]`, `[F Auberdine]`, `[P Ratchet]`, `[S Astranaar]` | Hearth, fly, get a flight path, set your hearth. |
| `[UI6928]` / `[CI4371,2]` / `[SP3561]` | Use an item, collect an item, cast a spell. |
| `[LE Polearms 1-]` | Show only if you haven't learned this skill. |

## Rules for editing the guide
- **Automatic navigation first.** Use QA/QC/QT and let Guidelime and QuestieDB find the place. Use `[G x,y Zone]` only for travel, trainers and vendors, or where the automatic arrow goes somewhere wrong.
- **Class steps always carry a filter,** for example `[A Warlock]`. A step without `[A ...]` is shown to every class.
- **Never change other classes' steps.** If a shared step has to change, it must still read correctly for every class.
- **Alliance only.** Every quest ID must be in QuestieDB and available to Alliance. Check it with `tools/questie.py`: it prints `races: Alliance` or `any`.
- **Chapters chain with `[NX]`.** When you add, rename or reorder a chapter:
  - update its `[N]` and the previous chapter's `[NX]`;
  - update the file list in `Guidelime_HarleyMage.toc`;
  - keep the level ranges contiguous (20-21, then 21-22).
- **Wording.** Use "Accept ...", "Turn in ...", "Kill ... for [QC...]" and "Reach level N." Keep each step to one action. Tips go on `[OC]` lines and stay short enough to read mid-fight.
- **Training.** Every class needs a `[T]` step at every even level from 2 to 42. The validator checks this. If a rank can wait when gold is short, add a "Short on gold? ... can wait" `[O]` line.
- **Bump the version** with every change: `## Version:` in `Guidelime_HarleyMage.toc` (minor for new content, patch for fixes). Add a line to `CHANGELOG.md`.
- **Make minimal diffs.** Never rewrite a whole file. Guidelime matches saved progress by exact step text, so rewording old steps resets players' ticks.

## Training-coverage check
`tools/validate.py` warns when a class has no `[T]` step at an even level, or at the level after it.
- It finds each step's level from `level-N` or `(N)` in the step text. Otherwise it estimates the level from the chapter's `[N A-B]` range and its `[XP]` markers.
- It is switched on in the toc with `## X-CheckTraining: 2-42`.
- Gaps that are accepted are listed in `## X-CheckTraining-Allow: Warlock:42; ...`. Level 42 is allowed for every class, because the 42 training is the first stop in Bethink's 42-44 Badlands chapter.
- The check gives warnings only. It never fails the run.

## Install and test in game
- **Install:**
  ```
  powershell -ExecutionPolicy Bypass -File install.ps1 -GameDir "D:\Games\World of Warcraft\_forever_"
  ```
  Use your own `_forever_` folder for `-GameDir`. The script copies `Guidelime_HarleyMage`, `Guidelime_Bethink` and `WarlockKit` into `Interface\AddOns`.
- **Load changes:**
  - Guide text changes: type `/reload` in game.
  - A new file or a `.toc` change: restart the game client.
- **Test:**
  - `/lime` opens Guidelime. Pick the chapter and check the arrow and the step text.
  - `/wk` lists the WarlockKit commands. `/wk test` saves a self-test to `WarlockKitDB.selftest` in `WTF\Account\<name>\SavedVariables\WarlockKit.lua`.

## How this guide was built (short version; see docs/)
1. **Route.** Bethink's Forever guides were the base. RestedXP's Forever routes were compared for ideas, such as zone order, hub order and where to put dungeons. No RestedXP text was copied. See `docs/route-comparison.md`.
2. **XP budget.** Quest XP is totalled per chapter (`tools/xp_budget.py`) so each `[XP N]` gate can actually be reached. Forever's dungeon XP is lower than in Classic.
3. **QuestieDB checks.** Every quest, NPC and item ID was looked up in the Forever QuestieDB, including Alliance availability and prerequisites.
4. **Gold-aware training.** Every even-level class training stop is in a city the route visits anyway. Ranks that can wait carry gold notes.
5. **Caster gear plan (Tailoring + Enchanting):**
   - **Wands:** Lesser Magic Wand, then Greater Magic Wand, then the dungeon wands Gravestone Scepter and Cookie's Stirring Rod, then the Twisted Nether Wand at 37. Dungeon cloth goes on `[O]` Need-roll lines.
   - **Tailoring:** the Pristine and Filigreed pieces.
6. **Class layers.** These are added one class at a time. `docs/harley-mage-next-steps.md` is the Mage worked example, and `docs/warlock-research.md` is the Warlock one.

## Checklist: adding a new class layer
1. Research the class. Save the sources in `docs/<class>-research.md`, covering the talent build with a level for each point, rotation by level band, pets or forms, and Forever-only changes.
2. Check the trainer list for every even level from 2 to 42. Put each `[T]` line in the city stop that matches that level.
3. Add the class quests. Get every ID from `tools/questie.py`, check it is Alliance or any, and use QA/QC/QT.
4. Add one `[A Class] [O] Talents: ...` line at the top of each chapter, and `[A Class] [OC] Rotation: ...` lines for each level band.
5. Add `[A Class] [O]` loot lines at dungeon steps. Don't duplicate the shared wand lines.
6. Run `python tools/validate.py` and fix every error and training warning.
7. Bump the toc version, add a `CHANGELOG.md` line, and test with `/reload` in game.

**Warlock worked example:**
- Succubus at 20: `[QA1716]`, then `[QA1738]` or `[QA65602]` with Takar, then `[QT1739]` or `[QT65603]` with Gakin.
- Felhunter at 30: 1798, 1758, 1802, 1804, then 1795.
- Felsteed at 40: 4488, then 4490.

## Common mistakes
- **Wrong or invented quest IDs.** Always check with `tools/questie.py`.
- **Horde-only quests.** The tool prints `races: Horde`. Many quests have separate Alliance and Horde IDs with the same name, such as 1716 for Alliance and 1507 for Horde.
- **A class step without an `[A ...]` filter.** Every class will see it.
- **A changed `[N]` name without updating the previous `[NX]` and the `.toc`.**
- **`[G]` coordinates on a quest step that QA/QC/QT could navigate to by itself.**
- **Cross-addon references.** `[NX 42-44 Badlands (Alliance)]` points into `Guidelime_Bethink`. The validator accepts that handoff, but Bethink's names must match exactly.
- **Brackets in plain text.** `[` starts a tag, so write normal prose without square brackets.

## Small-model mode (local 7-14B models)
- **Edit one chapter file at a time.** Open only the file you are changing and the glossary above.
- **Make minimal diffs.** Add or change single lines. Never paste back a whole file.
- **Don't guess IDs.** If you are unsure about a quest ID, run `python tools/questie.py quest <id>`.
- **Run the validator after every edit.**

**Worked edit 1: add a missing class training step.**
The validator says:
```
warning: training: Warlock has no [T] step at level 24 or 25
```
Find the city stop for level 24 in `A-23-25_Wetlands.lua`, which is the Ironforge training line for the other classes. Add one line after it:
```
[G50.08,7.45 Ironforge] [T] [A Warlock] Train Corruption III, Drain Soul II, Drain Mana and Sense Demons.
```
After the fix, the validator prints `Training coverage 2-42: 0 warnings`.

**Worked edit 2: fix a wrong quest ID.**
Before:
```
[A Warlock] Turn in [QT1507], then accept [QA1508].
```
`python tools/questie.py quest 1507` prints `races: Horde`. That quest is the Horde copy. The Alliance quest is 1716:
```
[A Warlock] [O] Turn in [QT1716], then accept [QA1738] for a Succubus or [QA65602] for an Incubus.
```
Check the new IDs with `python tools/questie.py quest 1716 quest 1738 quest 65602`, then run `python tools/validate.py`. It should end with `0 errors.`

## Build your own addon (short)
- **The `.toc` file.** A folder `MyAddon/` needs a `MyAddon.toc` containing:
  - `## Interface: 16001`
  - `## Title:`
  - `## SavedVariables: MyAddonDB`, which saves this table to WTF on logout;
  - then the list of Lua files to load, in order.
- **SavedVariables.** The table is `nil` until `PLAYER_LOGIN` or `ADDON_LOADED`. Merge your defaults in at that point, as `WarlockKit/Core.lua` does.
- **Forever API quirks we hit:**
  - Many old globals have moved to `C_Item`, `C_Container`, `C_Spell`, `C_SpellBook` and `C_UnitAuras`. Always fall back (`C_Item and C_Item.GetItemCount or GetItemCount`).
  - Some unit and aura values come back as "secret values". Check them with `issecretvalue` and wrap reads in `pcall`.
  - Spell IDs can differ from Classic, so find spells by name with a spellbook scan (`ns.BookSpells()` in WarlockKit).
  - Protected actions, such as casting from your own buttons or changing bars, need `SecureActionButtonTemplate` and are blocked in combat. Check `InCombatLockdown()` first.
  - Some events don't exist on this client. Register them inside `pcall`, as `ns.On` in `WarlockKit/Core.lua` does.
  - `GetPetActionInfo` returns values in a different order from 1.12. WarlockKit handles both orders.
- **Testing:** type `/reload` after editing Lua, and restart the client after a `.toc` change. Turn on Lua errors with `/console scriptErrors 1`.
