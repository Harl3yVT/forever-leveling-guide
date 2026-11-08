# Guide authoring instructions

## Scope and working files

AGENTS.md, this file, defines the reusable workflow for authoring original Guidelime zone guides; keep its instructions generic. LEVELS.md supplies the XP reference and planning rules. CONFIGURATION.md and PLAYSTYLE.md are editable inputs: CONFIGURATION.md specifies character combinations, starting locations, modes and companion priorities; PLAYSTYLE.md specifies routing, difficulty and training preferences. Apply both when creating or revising guides, and verify requirements before declaring support for a new configuration. Share modules where routes coincide, with verified applicability conditions, and use separate starting routes where needed.

Keep shared chapters applicable to their faction and mode. Use race restrictions for routes that need them, such as starting zones, and put class-specific quests, training, purchases, preparation and detours on individually restricted steps. Split mixed steps so ordinary quests, travel and dungeon clears remain available to everyone. Shared descriptions and handoffs must read as a general route. Class-specific detail follows CONFIGURATION.md; other classes can use the common route and train useful available abilities at city stops.

Prefer a simple shared route with built-in applicability tags. Accept small rough edges and modest extra travel rather than elaborate branching or workarounds. Give new arrivals a clear starting location and handle inherited deliveries conditionally. Budget the shared route without class-specific quest XP.

Keep README.md free of chapter inventories, dungeon schedules and version history. Put version history and change notes in NEWS.md.

Use the ignored `research/` folder for optional agent working material, including route overviews where helpful. Consult existing findings before researching again; preserve useful source pointers, dated observations, data conflicts and decision rationale in concise topical notes or structured data. Choose filenames to suit the work and prune obsolete or duplicated material. Create the folder as needed. Public files and guide loading must work without it; do not force-add its contents to Git.

## Workflow

1. Read the request, README.md, CONFIGURATION.md, PLAYSTYLE.md, LEVELS.md, the manifest, relevant guides and existing local research.
2. Gather and verify the evidence needed for the requested work.
3. Carry out the requested authoring or revision work, following the user's scope and these instructions.
4. Validate the result and report changes, material trade-offs, actual checks and limitations candidly and accurately.

### Evidence

- Inspect installed data and relevant game-flavor updates. Use QuestieDB for IDs, objectives, NPC levels/locations and prerequisites; inspect its schema and corrections. Raw zero counts can be placeholders.
- Check current official notes, online sources and static reference data for spells, trainers and companion skills; distinguish current evidence from historical fallbacks.
- Missing information is unknown, not zero. Never invent IDs, coordinates, rewards, drop rates or API behavior.
- Investigate unknown or apparently zero quest XP through targeted online research before finalizing XP accounting. Apply reasonable judgment to online XP figures, comparing quests of similar level and type and cross-checking implausible outliers.
- Unchanged evidence need not cause edits.

## Route design and text

Author every section as a fresh playthrough of one complete current route. Assume preceding steps were followed as currently written, independently of testing history. The resulting playable guide must stand on its own, free of change history, references to earlier versions or explanations of past corrections.

- Name modules `A–B Zone`, then `B–C Zone`, with matching boundaries. Use `[NX ...]` for onward handoffs, matching the destination `[N ...]` exactly. Replan zone order and boundaries when needed; update filenames, registered names, manifest order, handoffs and XP accounting together. Integrate dungeon preparation, the clear and turn-ins into zone chapters.
- Write concise actions. Research and use established game terminology at all times. Give quest pickups and turn-ins natural wording, such as “Accept …” and “Turn in …”, grouping interactions at the same NPC. Write quest completion actions in natural prose, followed by “for” and the quest link. Keep research, calculations, expected kill estimates and authoring explanations in local notes. Add a short terrain clarification only where navigation would otherwise be misleading; mention drops only when unusually poor.
- Apply recurring quest, training and utility patterns consistently across applicable routes, including inclusion, timing and wording.
- Place level gates at genuine, strong quest, training or encounter requirements, after suitable scheduled work and ready turn-ins. Write target levels explicitly as “Reach level N.”
- Before combining objectives, verify compatible targets, entrances, walkable paths, height differences and quest order. For ambiguous cave/surface routes or drop-started follow-ups, check quest descriptions and player comments online; nearby map pins or related enemy names do not establish shared kills, access or simultaneous availability. Prefer clarification within existing steps; add entrance waypoints only for non-obvious approaches.
- Write one default route that assumes the player completes every applicable step as described. Keep ordinary steps sequential. Use nonblocking flags selectively for conditional acquisition, dungeon objectives, parallel collection and manual skips; do not present ordinary work as discretionary. Conditional acquisition text is appropriate for eligible shares, rare quest starters, actual prerequisites, usable training ranks and hearth state. Sharing never bypasses requirements. Avoid distant pickup trips for unavailable shares.
- Combine two or three kill or collection quests naturally completed together in the same accessible area into one blocking completion step when timing, difficulty and applicability align. Require all included objectives before advancing.
- For collection accompanying several outings, such as lengthy ingredient gathering for a cooking quest, use one persistent nonblocking completion step and a required turn-in. Schedule the turn-in early enough to benefit from useful rewards and unlocks. Add map pins where useful; do not include travel instructions in persistent collection steps.
- Treat quest-starting drops commonly and normally obtained during scheduled questing as ordinary route content, including useful follow-ups. Assess availability using quest mechanics and player reports, accounting for loot restrictions when interpreting reported drop rates.
- Plan dungeon access from available evidence and reasonable assumptions. Uncertain access alone is not a reason to exclude a relevant dungeon.
- Explain substantial safety or travel reasons for dungeon omissions in chat and preserve the rationale in local research. Keep omission rationale out of playable guides. Excluded means absent; deferred means explicitly scheduled later.
- Respect other players' time: finish personal preparation and reach the activity before looking for a group. Groups are temporary and cover one dungeon or a couple of naturally connected local quests. For grouped escorts, warn before NPC interaction to wait until everyone has turned in the preceding quest, if any, and confirmed readiness. Keep that turn-in separate from the escort start.
- Routing in the large: Plan the overall leveling journey, balancing XP gains, travel and necessary preparation. Choose zone and chapter order, dungeon timing and training stops together; verify cross-chapter handoffs. Reconsider existing route choices when evidence supports an improvement.
- Routing in the zone: Group compatible work and give each visit a practical purpose. Collect useful available quests at planned visits, including later work, unless a concrete cost such as a quest timer justifies delay. Combine required returns with other useful work, preserving needed unlocks. Favor travel savings over earlier equipment rewards. Review travel and repeated visits with `tools/zone.py`; verify prerequisites, level requirements, terrain, applicability, incidental quest credit and independent groups before changing task order. Use the checkpoint shortfall heuristic in LEVELS.md as a review threshold.
- Routing in the hub: Optimize each hub visit as a bounded subproblem with `python3 tools/hub.py <plan.json>`; keep inputs and results in local research.
    - Arrival: Assume scheduled Hearthstone use and start at the bound inn. For flights, trams, boats, zeppelins, portals and teleports, use the local arrival point. When walking, use the preceding objective.
    - Exit: Use the next objective when walking onward, or the boarding or portal point when taking transport. Leave the endpoint free for Hearthstone or teleport departures usable at any stop.
    - Visits: Include unknown flight points and planned inn binding and supplies as required stops; omit acquisition prompts for flight points granted by default. Complete each NPC's or quest object's planned interactions before leaving, turning in ready quests before accepting new ones. Use one visit where feasible; model dependency-required returns as separate visits at the same coordinates.
    - Constraints: Supply verified ordering constraints, respect solver limits and review terrain and applicability before applying the order.
    - Classes: Exploit shared class-dependent routing patterns, especially starter-zone trainer referrals.
- Use ready Hearthstones liberally for substantial returns, including cave exits and city trips. Never wait idle for cooldown. Consider useful returns to the initial binding before the first rebind. State the binding and walk/flight fallback for Hearthstones; keep hearth steps nonblocking. Use combined hearth-or-flight steps where applicable.
- Verify spells/ranks, important class unlocks and active companion skills or vendor books. Name the trainer or seller and describe learning; purchasing alone is insufficient. Use `[SP ...]` for spell casts, with quest interactions and onward travel on separate steps.
- Give each included secondary profession its own tracked initial trainer step. Use native learned-state checks or manual completion for later training/book checklists; do not activate them by skill thresholds.

## Implementation and checks

Edit only this guide pack using Guidelime's built-in guide features. If a request requires complex workarounds or cannot be handled cleanly with them, explain the limitation and push for a simpler approach before proceeding. Extensions require explicit approval before exploration or implementation. Dependencies, client files and SavedVariables are read-only. Use supported content workarounds, but do not patch dependencies or inject compatibility overrides.

Use uppercase Markdown basenames with a lowercase `.md` extension. Use underscores in the top-level addon folder name, such as `Guidelime_Bethink`, and name its manifest `<addon-folder>_<flavor>.toc`, such as `Guidelime_Bethink_Camelot.toc`. Keep documentation and planning data out of the manifest's load list. Check syntax with the guide parser: `[A ...]` applies to a step, `[GA ...]` to a guide. Explicit `[G ...]` drives an arrow; `[L ...]` is a map pin. Use automatic navigation for quest pickups, objectives, turn-ins and item collections whenever Guidelime and its configured databases can determine a suitable destination. Explicit waypoints are allowed only when no automatic destination exists or a documented access or routing constraint requires a different location. Use map pins for passive collection trackers. Review navigation logic so the arrow leads to the intended next objective, including when a detour is skipped or unavailable. Keep collection target lists local when global drop-source lists are unsuitable.

Guidelime can rematch manual/skipped marks by exact step text when step counts change. Weigh the benefit of rewriting or regrouping steps against disruption to saved progress; preserve existing text where practical. Never edit saved flags.

Use `python3 tools/xp_budget.py --write` when a local XP plan is available, keeping its chronological events aligned with the chosen route and applicability conditions. The optional XP calculator totals chronological local planning data, reports shortfalls at level checkpoints and checks arithmetic and event order from authored input. `python3 tools/xp_budget.py --help` describes the input format; `--write` saves a local report. Without a local plan, no budget is calculated. Neither tool proves live behavior, timing or server XP. Keep tools independent of particular quests, zones, classes, chapter names and step counts.

Finally, run `python3 tools/validate.py <manifest.toc>` for an offline syntax check of all guides listed in the manifest. See `tools/guide_parser.py` for supported guide notation and validation limits.
