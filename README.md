# Harley's WoW Forever leveling guide (Alliance, 1-60)

A step-by-step leveling route for **WoW Forever** that runs inside the game with the
[Guidelime](https://www.curseforge.com/wow/addons/guidelime) addon. It works for **every Alliance race and class**:
Guidelime only shows you the steps for your own class (class training, demon books, wands and so on).

- **1-42: Harley's route.** It starts in Elwynn Forest, Dun Morogh, Teldrassil or Zephras Isle, depending on your race. Then it goes Loch Modan, Westfall, Darkshore, Ashenvale, Redridge, Duskwood, Wetlands, Hillsbrad, Stranglethorn, Thousand Needles, Desolace, Arathi and Dustwallow.
- **42-60: Bethink's guides.** The route hands off to these automatically at 42.

## Install (5 minutes)

### 1. Get the two addons it needs

Open the **CurseForge app**, pick **World of Warcraft**, and switch the game version at the top to **Forever**. Then search for and install:

- **Guidelime**
- **QuestieDB**

### 2. Get this guide

1. Open the [latest release](https://github.com/Harl3yVT/forever-leveling-guide/releases/latest) and download `forever-leveling-guide-<version>.zip`.
2. Extract the ZIP.
3. Copy these folders into your game's AddOns folder:

   - `Guidelime_HarleyMage`
   - `Guidelime_Bethink`
   - `HarleyLib` and `WarlockKit` (optional, only useful on a Warlock: type `/wk` in game; WarlockKit needs HarleyLib)

   Or run `install.ps1 -GameDir "<your _forever_ folder>"` from the extracted folder.

   The AddOns folder is usually:

   ```
   C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns
   ```

   It's wherever your `_forever_` folder is. Copy the folders themselves, not a `forever-leveling-guide-main` folder that holds them.

### 3. In game

1. On the character screen, open **AddOns** and make sure **Guidelime**, **QuestieDB**, **Guidelime: Harley Mage (alts)** and **Guidelime: Bethink** are all ticked.
2. Log in and type `/lime`.
3. Open the **Harley Mage** group. The name says Mage, but the guide covers every class.
4. Pick the chapter for where you are:

| Your race | Start with |
| --- | --- |
| Human | **1-11 Elwynn Forest (Harley)** |
| Dwarf, Gnome | **1-11 Dun Morogh (Harley)** |
| Night Elf | **1-11 Teldrassil (Harley)** |
| Skyborne | **1-14 Zephras Isle (Harley)** |
| Already level 11-14 | **11-14 Loch Modan (Harley)** (Skyborne go straight to 14-16 Westfall, then Darkshore 16-20 and Ashenvale 20-21) |
| Higher level | The chapter that matches your level |

Each chapter loads the next one when you finish it. To skip a step, like a quest you've
already done, tick its box.

## Updating

Download the newest release ZIP and unzip the folders over the old ones in `Interface\AddOns`, replacing them (or run `install.ps1` again: it backs up the old folders to `_forever_\AddOn-backups` first). Your progress in the guide is kept. `CHANGELOG.md` lists what changed.

## Found a wrong step?

Open an issue with the **Wrong or missing guide step** form (Issues tab, New issue).

## Editing with AI

You can change the guide, or build your own addons, with any AI coding tool or a local model (Claude Code, Cursor, ChatGPT, Ollama, LM Studio and so on).

- Start with [AGENTS.md](AGENTS.md). Most AI tools read it automatically. It explains the tags, the rules and how to check the work.
- [docs/ai-prompt-template.md](docs/ai-prompt-template.md) is a ready-to-paste prompt for jobs like "add or fix steps for level X-Y".
- Check any edit with one command (plain Python 3.10+, nothing to install):

  ```
  python tools/validate.py
  ```

## Credits and license

Built on [Bethink's Guidelime guides](Guidelime_Bethink/README.md) for WoW Forever. The route text in
`Guidelime_HarleyMage` is adapted from them, with extra steps for training, professions, wands and the Forever quests.
GPLv3, see [LICENSE](LICENSE).
