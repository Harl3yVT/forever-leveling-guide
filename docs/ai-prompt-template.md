# Prompt template: add or fix guide steps

Copy everything inside the box into your AI tool (Claude Code, Cursor, ChatGPT, Ollama, LM Studio and so on). Then replace the `<...>` parts.

```
You are editing a WoW Forever leveling guide (Guidelime addon) in this repo.
First read AGENTS.md completely, then CHANGELOG.md, then the open issues (gh issue list) if you can.

Task: <add | fix> steps for <class, e.g. Warlock> from level <X> to <Y>.
Details: <what is wrong or missing, e.g. "the level-26 training step lists the wrong spells",
         or paste the issue text, including chapter name and step text>.

Rules:
- Edit only the chapter file(s) in Guidelime_HarleyMage/guides/ that cover levels X-Y. One file at a time.
- Make minimal diffs: add or change single lines, never rewrite or reformat a whole file.
- Class-only steps must carry [A <Class>]. Do not change or remove other classes' steps;
  a shared step must stay correct for every class.
- Use [QA]/[QC]/[QT] with real quest IDs. If unsure of an ID, run:
    python tools/questie.py quest <id>
  and only use IDs it finds with races Alliance or any. Never guess an ID.
- Use [G x,y Zone] only for travel, trainers and vendors.
- After editing run:
    python tools/validate.py
  It must end with "0 errors." and "0 warnings" for training coverage. Fix anything it reports.
- Bump "## Version:" in Guidelime_HarleyMage/Guidelime_HarleyMage.toc (patch for fixes, minor for new content)
  and add one line to CHANGELOG.md.

When done, show me the diff and the validator output.
```
