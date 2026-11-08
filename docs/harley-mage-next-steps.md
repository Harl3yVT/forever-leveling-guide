# Worked example: how the Mage layer was added

The Warlock layer (0.5.0) followed the same steps. See `warlock-research.md`.

1. **Research.** We read three Forever mage leveling guides (method.gg, conquestcapped.com and warcrafttavern.com) and chose one build: "Questing Frost".
2. **Talent lines.** At the top of each chapter we added one line: `[A Mage] [O] Talents: At N, <talent>.`

   | Level | Talent |
   | --- | --- |
   | 10-14 | Improved Frostbolt 5/5 |
   | 15-19 | Frostbite 2/3, Ice Shards 3/5 |
   | 20 | Ice Lance |
   | 21-24 | Frost Channeling 3/3, Improved Blizzard 1/3 |
   | 25-26 | Ice Shards 5/5 |
   | 27-29 | Shatter 3/3 |
   | 30 | Fingers of Frost 1/2 |
   | 31-35 | Improved Cone of Cold, Cold Snap |
   | 40 | Ice Barrier |
3. **Training stops.** Every even level got a stop, with the city chosen to match the route. Forever-specific spells were checked, such as Ice Lance at 20 and Frostfire Bolt at 40.
4. **Rotation.** We added `[A Mage] [OC] Rotation: ...` lines for each level band.
5. **Professions and gear.** Tailoring and Enchanting are shared with Priest and Warlock, so those lines use `[A Priest,Mage,Warlock]`: Pristine Tailoring pieces, the Lesser and Greater Magic Wand, the dungeon wands, and the Twisted Nether Wand.
6. **Helper addon.** MageKit is the model WarlockKit followed. It has a rebuff button, alerts, a talent button that follows the plan above, and a leveling bar layout.
7. **Checks.** We ran `python tools/validate.py`, bumped the toc version, and tested in game with `/reload`.
