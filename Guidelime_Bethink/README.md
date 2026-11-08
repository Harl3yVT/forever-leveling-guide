# Bethink’s Guidelime framework

A framework for creating customized Guidelime leveling guides with AI. Use the included guides as supplied, or adapt the character configuration and play-style instructions to your preferences and ask an AI agent to build or revise the affected guides.

## Included guides

The included Softcore guides cover all 56 race–class combinations across Alliance and Horde from level 1 to 60. Race-specific starting routes lead into shared faction journeys, with class-specific steps throughout.

The guides are written for solo players who form groups for dungeons and tougher outdoor quests. They generally include one clear of each relevant leveling dungeon, with preparation, dungeon quests and turn-ins integrated into the route. The aim is a varied leveling journey with useful equipment rewards.

Class steps cover important ability unlocks, useful spells, companion training and equipment upgrades. The routes use flight points, Hearthstone returns and compact quest-hub visits to reduce travel. The guides include camping and training in the secondary professions (First Aid, Cooking and Fishing), while primary professions remain your choice.

See [CONFIGURATION.md](CONFIGURATION.md) for the full matrix, starting locations and class priorities.

> [!NOTE]
> The included guides were generated with AI by Bethink and serve to demonstrate the framework. While the framework’s instructions for AI guide authoring were extensively refined through playthrough testing, you should not assume that the resulting guides have been fully play-tested.

## Adapting the guides

To adapt the guides to your preferences, edit the relevant input files:

- To change the play style, including profession preferences, edit [PLAYSTYLE.md](PLAYSTYLE.md).
- To change character configurations or class priorities, edit [CONFIGURATION.md](CONFIGURATION.md).

After either change, ask an AI agent to update the affected guides.

## Installation and use

The dependencies are **Guidelime** and **QuestieDB**.

1. Install versions of these dependencies compatible with your game client in its `Interface/AddOns` folder.
2. Place the `Guidelime_Bethink` folder alongside them in the same `AddOns` folder.
3. Enable the addons and use `/reload` if already logged in.
4. Use `/lime` to select a Bethink chapter.

The pack's manifest is `Guidelime_Bethink_Camelot.toc`.

Keep automatic updates disabled for this pack in your addon manager to preserve your customizations. Back up your changes before a manual update.

## Creating a release ZIP

From the addon folder, run:

```sh
python3 tools/package.py
```

This creates `dist/Guidelime_Bethink-<version>.zip` using the version in the `.toc` manifest. It includes registered guides, documentation, the license and authoring tools. Local research, caches and previous archives are excluded. Running it again replaces the ZIP for the same version.

## License

Licensed under the [GNU General Public License version 3 (GPLv3)](LICENSE). Copyright (c) 2026 Bethink.

Guide authoring includes the use of reference data from [QuestieDB](https://github.com/Questie/QuestieDB). Thanks to the contributors of QuestieDB and [Questie](https://github.com/Questie/Questie).
