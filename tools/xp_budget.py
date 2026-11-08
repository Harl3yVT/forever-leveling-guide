#!/usr/bin/env python3
"""Calculate a chronological XP budget from optional local planning data.

Plan format: quests maps arbitrary IDs to {reward, kind, acquisition_extra};
kind is outdoor or dungeon; null rewards are unknown. acquisition_extra is optional.
chapters contains {name, events}. Events use type=quest (id), level (level),
enter (name, level), or clear (name). Keep the selected route's events in order.
A final reference row with no next-level XP bar marks the cap. Cap gates stop
later earnings without filling any earlier shortfall; cap clears earn no XP.
This calculator does not select quests or infer a route from guide prose.
Checkpoints report XP shortfalls without adding earnings.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ROOT / 'Guidelime_Bethink' / 'LEVELS.md'


def thresholds(path):
    rows = re.findall(r'^\| (\d+) \| ([\d,]+|—) \| ([\d,]+) \|', path.read_text(), re.M)
    assert rows, 'No XP table found'
    bars, cumulative = {}, {}
    previous, total = None, 0
    for raw_level, raw_bar, raw_total in rows:
        level = int(raw_level)
        assert previous is None or level == previous + 1, 'XP table has a gap or duplicate'
        cumulative[level] = int(raw_total.replace(',', ''))
        assert cumulative[level] == total, 'Inconsistent cumulative XP table'
        if raw_bar != '—':
            bars[level] = int(raw_bar.replace(',', ''))
            assert bars[level] > 0
            total += bars[level]
        previous = level
    return bars, cumulative


def calculate(plan, bars, cumulative, without_extras=False):
    coefficient = plan.get('outdoor_total_coefficient', 2)
    fraction = plan.get('clear_bar_fraction', 0.2)
    assert coefficient > 0 and 0 <= fraction <= 1, 'Invalid earnings coefficients'
    total = cumulative[plan.get('start_level', min(cumulative))]
    final_level = max(cumulative)
    cap = final_level if final_level not in bars else None
    max_xp = cumulative[cap] if cap is not None else float('inf')
    at_cap = plan.get('start_level', min(cumulative)) == cap
    paid, entered, cleared, unknown, chapters = set(), {}, set(), set(), []
    for chapter in plan['chapters']:
        row = dict(name=chapter['name'], outdoor=0, dungeon=0, kills=0, gates=[])
        for event in chapter['events']:
            kind = event['type']
            if kind == 'quest':
                key = str(event['id'])
                assert key not in paid, f'Duplicate reward event: {key}'
                paid.add(key)
                quest = plan['quests'][key]
                if without_extras and quest.get('acquisition_extra', False):
                    continue
                reward = quest['reward']
                if reward is None:
                    unknown.add(key); continue
                assert reward >= 0 and quest['kind'] in ('outdoor', 'dungeon'), f'Invalid reward: {key}'
                credit = reward * (coefficient if quest['kind'] == 'outdoor' else 1)
                credit = 0 if at_cap else min(credit, max_xp - total)
                row['outdoor' if quest['kind'] == 'outdoor' else 'dungeon'] += credit
                total += credit
            elif kind == 'level':
                level = event['level']
                row['gates'].append((f'Level {level}', level, max(0, cumulative[level] - total)))
                if level == cap:
                    at_cap = True
            elif kind == 'enter':
                name, level = event['name'], event['level']
                assert name not in entered, f'Duplicate clear entry: {name}'
                assert level in bars or level == cap, f'No entry-level XP bar: {level}'
                entered[name] = level
                row['gates'].append((f'Enter {name}', level, max(0, cumulative[level] - total)))
                if level == cap:
                    at_cap = True
            elif kind == 'clear':
                name = event['name']
                assert name in entered and name not in cleared, f'Invalid clear event: {name}'
                credit = round(fraction * bars.get(entered[name], 0))
                credit = 0 if at_cap else min(credit, max_xp - total)
                cleared.add(name); row['kills'] += credit; total += credit
            else:
                raise ValueError(f'Unknown event type: {kind}')
        row['exit'] = total
        chapters.append(row)
    assert set(entered) == cleared, 'An entered clear has no completion event'
    return chapters, unknown, entered


def render(plan, bars, cumulative):
    full, unknown, clears = calculate(plan, bars, cumulative)
    reduced, _, _ = calculate(plan, bars, cumulative, True)
    coefficient = plan.get('outdoor_total_coefficient', 2)
    fraction = plan.get('clear_bar_fraction', 0.2)
    fmt = lambda value: f'{value:,.0f}'
    out = ['# XP budget', '', 'Calculated from local chronological planning data; values are estimates.', '',
           f'Outdoor total: {coefficient:g} × reward XP. Dungeon rewards: once. Each clear: {fraction:g} × its entry-level XP bar.', '',
           '| Chapter | Outdoor total | Dungeon rewards | Clear combat | Cumulative XP | XP without acquisition extras |',
           '| --- | ---: | ---: | ---: | ---: | ---: |',]
    for row, low in zip(full, reduced):
        out.append('| ' + row['name'] + ' | ' + ' | '.join(fmt(value) for value in
                   (row['outdoor'], row['dungeon'], row['kills'], row['exit'], low['exit'])) + ' |')
    out += ['', '## Checkpoint shortfalls', '', '| Chapter | Checkpoint | Level | Full plan | Without acquisition extras |', '| --- | --- | ---: | ---: | ---: |']
    gaps = 0
    for row, low in zip(full, reduced):
        for (label, level, gap), (_, _, low_gap) in zip(row['gates'], low['gates']):
            if gap or low_gap:
                gaps += 1
                out.append(f"| {row['name']} | {label} | {level} | {fmt(gap)} | {fmt(low_gap)} |")
    if not gaps:
        out.append('| — | No shortfalls | — | 0 | 0 |')
    out += ['', '## Clears', '', '| Clear | Planned entry level | Combat XP estimate |', '| --- | ---: | ---: |']
    for name, level in clears.items():
        out.append(f'| {name} | {level} | {fmt(round(fraction * bars.get(level, 0)))} |')
    out += ['', 'Unpriced reward IDs: ' + (', '.join(sorted(unknown)) or 'none') + '.', '',
            'Shortfalls are reported without adding XP. Surplus carries forward; rewards are credited only at their chronological events.', '',
            'A final table row without a next-level XP bar marks the cap. XP stops there; a cap gate stops later earnings without filling an earlier shortfall. Clears entered at the cap earn no XP.', '',
            'Keep the input plan aligned with the chosen guide route and applicability conditions. The calculator checks arithmetic and event order, not gameplay.']
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('plan', nargs='?', type=Path, help='JSON plan; defaults to research/xp_plan.json when present')
    parser.add_argument('--levels', type=Path, default=LEVELS)
    parser.add_argument('--write', action='store_true', help='Save the report in the local research folder')
    parser.add_argument('--output', type=Path, default=ROOT / 'research/XP_BUDGET.md')
    args = parser.parse_args()
    path = args.plan or ROOT / 'research/xp_plan.json'
    if not path.exists():
        if args.plan is not None:
            parser.error(f'Plan does not exist: {path}')
        parser.exit(message='No local XP plan found. Supply a JSON plan; see --help for its format.\n')
    plan = json.loads(path.read_text())
    text = render(plan, *thresholds(args.levels))
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f'Saved XP budget: {args.output}')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
