#!/usr/bin/env python3
"""Audit waypoint traces for opportunities to consolidate visits.

Usage: python3 tools/zone.py manifest.toc --race 'Night Elf' [--class Druid]
Distances use unscaled map-coordinate units. Parameters control findings only;
trace distances use applicable G points and nearest eligible QuestieDB positions
for unlocated quest/item work. Optional located steps are included. Source gaps
and transport interruptions remain visible.
"""

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from math import hypot, isfinite
from pathlib import Path
import re
import sys

try:
    from .guide_parser import Applicability, QuestReference, SkillReference, read_guide, validate_guide
    from .questie import QuestieDB
    from .validate import validate_manifest
except ImportError:
    from guide_parser import Applicability, QuestReference, SkillReference, read_guide, validate_guide
    from questie import QuestieDB
    from validate import validate_manifest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def default_database():
    manifest = next(ROOT.glob('*.toc'))
    flavor = manifest.stem.rsplit('_', 1)[-1]
    return QuestieDB(ROOT.parent / 'QuestieDB' / f'QuestieDB_{flavor}.toc')


@dataclass(frozen=True)
class Profile:
    faction: str
    race: str
    cls: str
    mode: str = "Softcore"

    @property
    def id(self):
        return "-".join((self.faction, self.race, self.cls, self.mode))


@dataclass(frozen=True)
class Parameters:
    near: float = 0.5
    departure: float = 5.0
    visit: float = 0.3
    excursion: float = 15.0
    saving: float = 3.0
    include_gaps: bool = False

    def check(self):
        if not all(isfinite(x) and x >= 0 for x in (self.near, self.departure, self.visit, self.excursion, self.saving)):
            raise ValueError("Distance parameters must be finite and nonnegative")
        if self.departure <= self.near or self.visit > self.near:
            raise ValueError("Require departure > near and visit <= near")


def profiles_from_configuration(path):
    profiles = []
    header = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if header is None:
            if {"Faction", "Race", "Class", "Mode"}.issubset(cells):
                header = cells
            continue
        if len(cells) != len(header) or all(re.fullmatch(r"[: -]+", c) for c in cells):
            continue
        row = dict(zip(header, cells))
        profiles.append(Profile(row["Faction"], row["Race"].replace(" ", ""), row["Class"], row["Mode"]))
    if not profiles:
        raise ValueError("Configuration contains no character profiles")
    return list(dict.fromkeys(profiles))


def applies(condition, profile):
    if condition is None:
        return True
    choices = defaultdict(set)
    for term in condition.conditions:
        if term.kind in {"class", "race", "faction", "mode"}:
            choices[term.kind].add(term.name)
    values = {"class": profile.cls, "race": profile.race, "faction": profile.faction, "mode": profile.mode}
    return all(values[kind] in names for kind, names in choices.items())


def distance(a, b):
    return hypot(a["x"] - b["x"], a["y"] - b["y"])


def point_segment(point, a, b):
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    square = dx * dx + dy * dy
    fraction = max(0.0, min(1.0, ((point["x"] - a["x"]) * dx + (point["y"] - a["y"]) * dy) / square)) if square else 0.0
    return hypot(point["x"] - a["x"] - fraction * dx, point["y"] - a["y"] - fraction * dy), fraction


class QuestLocations:
    """Resolve quest and item locations using the nearest eligible position."""

    def __init__(self, database, guides):
        self.database = database
        self.names = dict(database.zone_names)
        for guide in guides:
            for step in guide.steps:
                for tag in step.tags:
                    if tag.code in ('G', 'L'):
                        area = database.zone_id(tag.value.zone)
                        if area is not None:
                            self.names[area] = tag.value.zone

    def resolve(self, step, guide, previous, profile):
        db = self.database
        targets = tuple(tag.value.npc_id for tag in step.tags if tag.code == 'TAR')
        groups = []
        for tag in step.tags:
            if tag.code in ('QA', 'QC', 'QT'):
                quest = db.record('Quest', tag.value.quest_id)
                preferred = quest.get('zoneOrSort') if tag.code == 'QC' else None
                groups.extend((points, preferred) for points in db.quest_locations(
                    tag.value.quest_id, tag.code, tag.value.objectives, targets, profile.faction))
            elif tag.code == 'CI':
                groups.append((db.item_locations(tag.value.item_id, targets), None))
        chapter = re.sub(r'^\d+\s*-\s*\d+\s+', '', guide.name or '').split(' (')[0]
        chapter_area = db.zone_id(chapter)
        result = []
        for points, preferred in groups:
            if not points:
                return []
            areas = {p.area_id for p in points}
            previous_area = db.zone_id(previous['zone']) if previous else None
            area = next((area for area in (previous_area, preferred, chapter_area) if area in areas), None)
            if area is None:
                if len(areas) != 1:
                    return []
                area = next(iter(areas))
            candidates = [p for p in points if p.area_id == area]
            if area not in self.names:
                return []
            if previous and previous_area == area:
                chosen = min(candidates, key=lambda p: hypot(p.x - previous['x'], p.y - previous['y']))
            else:
                chosen = candidates[0]
            previous = {'x': chosen.x, 'y': chosen.y, 'zone': self.names[area],
                        'column': None, 'inferred': True,
                        'database_source': {'entity': chosen.entity, 'id': chosen.entity_id, 'area_id': area}}
            result.append(previous)
        return result


def build_trace(guides, profile, locations=None):
    if locations is None:
        locations = QuestLocations(default_database(), guides)
    events, points, legs = [], [], []
    counts = Counter()
    episode, zone = -1, None
    previous = None
    for guide in guides:
        if not applies(guide.applicability, profile):
            continue
        for step in guide.steps:
            if not all(applies(tag.value, profile) for tag in step.tags if tag.code == "A"):
                counts["filtered_character_steps"] += 1
                continue
            if any((isinstance(tag.value, Applicability) and any(c.kind == "profession" for c in tag.value.conditions))
                   or (isinstance(tag.value, SkillReference) and tag.value.is_profession)
                   for tag in step.tags):
                counts["filtered_profession_steps"] += 1
                continue
            codes = {tag.code for tag in step.tags}
            coordinates = [tag for tag in step.tags if tag.code == "G"]
            transport = bool(codes & {"H", "F"})
            background = "O" in codes and bool(codes & {"QC", "CI"}) and not coordinates and not transport
            resolved = []
            if not coordinates and not background and not transport:
                resolved = locations.resolve(step, guide, previous, profile)
            event = {
                "file": step.location.path, "line": step.location.line, "text": step.raw,
                "guide": guide.name, "codes": sorted(codes),
                "quests": [{"kind": tag.code, **asdict(tag.value)} for tag in step.tags if isinstance(tag.value, QuestReference)],
                "conditional": bool(codes & {"O", "OC"}) or any(
                    isinstance(tag.value, Applicability) and any(c.kind == "item" for c in tag.value.conditions) for tag in step.tags),
                "transport_before": transport and not coordinates,
                "transport_after": transport,
                "gap": not coordinates and not resolved and not background and not transport,
                "background": background,
                "inferred": bool(resolved),
            }
            event_index = len(events)
            events.append(event)
            counts["eligible_steps"] += 1
            counts["located_steps"] += bool(coordinates or resolved)
            counts["inferred_steps"] += bool(resolved)
            counts["unlocated_steps"] += event["gap"]
            counts["background_steps"] += background
            counts["transport_steps"] += transport
            located = [{'x': tag.value.x, 'y': tag.value.y, 'zone': tag.value.zone,
                        'column': tag.location.column, 'inferred': False} for tag in coordinates] or resolved
            for location in located:
                if location['zone'] != zone:
                    episode += 1
                    zone = location['zone']
                points.append({"id": len(points), "event": event_index, "episode": episode,
                               **location})
                previous = location
                counts['inferred_points'] += location['inferred']
            if transport:
                previous = None
    for a, b in zip(points, points[1:]):
        if a["episode"] != b["episode"]:
            continue
        between = range(a["event"] + 1, b["event"])
        gaps = [i for i in between if events[i]["gap"]]
        interrupted = a["event"] != b["event"] and (
            events[a["event"]]["transport_after"] or events[b["event"]]["transport_before"]
            or any(events[i]["transport_before"] or events[i]["transport_after"] for i in between))
        legs.append({"from": a["id"], "to": b["id"], "episode": a["episode"], "zone": a["zone"],
                     "distance": distance(a, b), "gaps": gaps, "transport": interrupted})
    counts["points"] = len(points)
    counts["zone_visits"] = episode + 1
    counts["walking_legs"] = sum(not leg["transport"] for leg in legs)
    counts["gap_legs"] = sum(bool(leg["gaps"]) and not leg["transport"] for leg in legs)
    stats = dict(counts)
    stats["trace_distance"] = sum(leg["distance"] for leg in legs if not leg["transport"])
    stats["gap_distance"] = sum(leg["distance"] for leg in legs if not leg["transport"] and leg["gaps"])
    stats["continuous_distance"] = stats["trace_distance"] - stats["gap_distance"]
    zones = []
    for number in range(episode + 1):
        anchors = [point for point in points if point["episode"] == number]
        edges = [leg for leg in legs if leg["episode"] == number and not leg["transport"]]
        zones.append({"episode": number, "zone": anchors[0]["zone"], "points": len(anchors),
                      "trace_distance": sum(leg["distance"] for leg in edges),
                      "gap_legs": sum(bool(leg["gaps"]) for leg in edges)})
    return {"profile": asdict(profile), "profile_id": profile.id, "stats": stats,
            "events": events, "points": points, "legs": legs, "zones": zones}


def make_visits(trace, radius):
    visits = []
    edges = {leg["from"]: leg for leg in trace["legs"]}
    for point in trace["points"]:
        edge = edges.get(point["id"] - 1)
        if (visits and visits[-1]["episode"] == point["episode"] and edge
                and not edge["gaps"] and not edge["transport"] and distance(visits[-1], point) <= radius):
            visits[-1]["end"] = point["id"]
        else:
            visits.append({"id": len(visits), "start": point["id"], "end": point["id"],
                           "x": point["x"], "y": point["y"], "episode": point["episode"], "zone": point["zone"]})
    return visits


def removal(trace, visit, edges):
    points = trace["points"]
    start, end = visit["start"], visit["end"]
    if start == 0 or end + 1 == len(points):
        return None, ["boundary"]
    adjacent = [edges.get(index) for index in range(start - 1, end + 1)]
    if any(edge is None for edge in adjacent):
        return None, ["zone_boundary"]
    if any(edge["transport"] for edge in adjacent):
        return None, ["transport"]
    uncertainty = ["unlocated_steps"] if any(edge["gaps"] for edge in adjacent) else []
    cost = sum(edge["distance"] for edge in adjacent) - distance(points[start - 1], points[end + 1])
    return max(0.0, cost), uncertainty


def source_ref(trace, point_index):
    point = trace["points"][point_index]
    event = trace["events"][point["event"]]
    return {"file": event["file"], "line": event["line"], "text": event["text"]}


def find_candidates(trace, parameters):
    parameters.check()
    points, events, legs = trace["points"], trace["events"], trace["legs"]
    visits = make_visits(trace, parameters.visit)
    edges = {leg["from"]: leg for leg in legs}
    episode_legs = defaultdict(list)
    for leg in legs:
        episode_legs[leg["episode"]].append(leg)
    history = defaultdict(list)
    removals = {visit["id"]: removal(trace, visit, edges) for visit in visits}
    conditional_prefix = [0]
    for event in events:
        conditional_prefix.append(conditional_prefix[-1] + (event["conditional"] and "G" in event["codes"]))
    prefix, transport_prefix = [0.0], [0]
    for point in points:
        edge = edges.get(point["id"])
        prefix.append(prefix[-1] + (edge["distance"] if edge and not edge["transport"] else 0.0))
        transport_prefix.append(transport_prefix[-1] + bool(edge and edge["transport"]))
    candidates = []

    def candidate(kind, visit, other, saving, uncertainty, interval, **extra):
        first, last = interval
        if conditional_prefix[last + 1] != conditional_prefix[first]:
            uncertainty = [*uncertainty, "conditional_steps"]
        return {"kind": kind, "profile_id": trace["profile_id"], "zone": visit["zone"],
                "episode": visit["episode"], "x": visit["x"], "y": visit["y"],
                "visit": visit["id"], "other": other, "saving": saving,
                "uncertainty": sorted(set(uncertainty)), "event_range": [first, last],
                "source": source_ref(trace, visit["start"]), **extra}

    for visit in visits:
        peak = 0.0
        for previous in reversed(history[visit["episode"]]):
            separation = distance(visit, previous)
            peak = max(peak, separation)
            if separation > parameters.near:
                continue
            length = prefix[visit["start"]] - prefix[previous["end"]]
            if peak >= parameters.departure and length >= parameters.excursion:
                first = points[previous["end"]]["event"]
                last = points[visit["start"]]["event"]
                uncertain = []
                if any(event["gap"] for event in events[first:last + 1]):
                    uncertain.append("unlocated_steps")
                if transport_prefix[visit["start"]] != transport_prefix[previous["end"]]:
                    uncertain.append("transport")
                alternatives = [removals[previous["id"]], removals[visit["id"]]]
                priced = [(value, reasons) for value, reasons in alternatives if value is not None]
                saving, reasons = max(priced, key=lambda pair: pair[0]) if priced else (None, ["boundary"])
                candidates.append(candidate("return", visit, previous["id"], saving, uncertain + reasons,
                    (first, last), excursion=length, peak=peak,
                    earlier_source=source_ref(trace, previous["start"])))
            break  # One return per arrival; retain the full history for the search.
        history[visit["episode"]].append(visit)

        removable, removal_reasons = removals[visit["id"]]
        if removable is None:
            continue
        best = {}
        for leg in episode_legs[visit["episode"]]:
            if leg["transport"]:
                continue
            if not (leg["to"] < visit["start"] or leg["from"] > visit["end"]):
                continue
            a, b = points[leg["from"]], points[leg["to"]]
            closest, fraction = point_segment(visit, a, b)
            if not 0 < fraction < 1 or closest > parameters.near:
                continue
            if min(distance(visit, a), distance(visit, b)) < parameters.departure:
                continue
            uncertainty = [*removal_reasons, *(["unlocated_steps"] if leg["gaps"] else [])]
            if uncertainty and not parameters.include_gaps:
                continue
            internal = sum(distance(points[index], points[index + 1])
                           for index in range(visit["start"], visit["end"]))
            insertion = (distance(a, points[visit["start"]]) + internal
                         + distance(points[visit["end"]], b) - leg["distance"])
            saving = removable - insertion
            if saving < parameters.saving:
                continue
            direction = "earlier" if leg["to"] < visit["start"] else "later"
            first = min(points[visit["start"]]["event"], a["event"])
            last = max(points[visit["end"]]["event"], b["event"])
            start_point = min(visit["start"], leg["from"])
            end_point = max(visit["end"], leg["to"])
            if transport_prefix[end_point] != transport_prefix[start_point]:
                continue
            item = candidate("passage", visit, leg["from"], saving, uncertainty, (first, last),
                direction=direction, closest=closest, fraction=fraction,
                leg_sources=[source_ref(trace, leg["from"]), source_ref(trace, leg["to"])])
            if direction not in best or saving > best[direction]["saving"]:
                best[direction] = item
        candidates.extend(best.values())
    return visits, candidates


def grouped_findings(candidates, radius):
    groups = []
    buckets = defaultdict(list)
    for item in candidates:
        bucket = buckets[item["profile_id"], item["episode"], item["kind"], item.get("direction")]
        existing = next((group for group in bucket if distance(group, item) <= radius), None)
        if existing is None:
            existing = {key: item[key] for key in ("profile_id", "episode", "zone", "kind", "x", "y")}
            existing.update(direction=item.get("direction"), occurrences=[])
            groups.append(existing)
            bucket.append(existing)
        existing["occurrences"].append(item)
    combined = {}
    for group in groups:
        signature = tuple(sorted((item["source"]["file"], item["source"]["line"],
            tuple((ref["file"], ref["line"]) for ref in item.get("leg_sources", [item.get("earlier_source", item["source"])])))
            for item in group["occurrences"]))
        key = group["kind"], group["zone"], group["direction"], signature
        if key not in combined:
            combined[key] = {**group, "profiles": [], "occurrences": []}
        combined[key]["profiles"].append(group["profile_id"])
        combined[key]["occurrences"].extend(group["occurrences"])
    result = list(combined.values())
    for group in result:
        values = [item["saving"] for item in group["occurrences"] if item["saving"] is not None]
        group["max_saving"] = max(values) if values else None
        group["uncertainty"] = sorted({reason for item in group["occurrences"] for reason in item["uncertainty"]})
    result.sort(key=lambda g: (bool(g["uncertainty"]), -(g["max_saving"] or 0),
                              g["zone"], g["kind"], g["occurrences"][0]["source"]["file"],
                              g["occurrences"][0]["source"]["line"]))
    return result


def audit(guides, profiles, parameters, database=None):
    parameters.check()
    if database is None:
        database = default_database()
    traces, candidates = [], []
    locations = QuestLocations(database, guides)
    for profile in profiles:
        trace = build_trace(guides, profile, locations)
        visits, found = find_candidates(trace, parameters)
        traces.append({**trace, "visits": visits})
        candidates.extend(found)
    hashes = {guide.location.path: hashlib.sha256(Path(guide.location.path).read_bytes()).hexdigest()
              for guide in guides if Path(guide.location.path).is_file()}
    return {"schema": 2, "parameters": asdict(parameters), "units": "map coordinate units",
            "database": {"path": str(database.path), "flavor": database.metadata.get('X-Flavor')},
            "assumptions": ["Explicit G points take precedence; L pins are contextual",
                "Nearest eligible QuestieDB spawn fills missing quest/item locations",
                "Optional located steps included; passive collection does not create a visit",
                "Profession applicability and skill-reference steps excluded",
                "Unlocated steps retained as gaps",
                "Transport boundaries use H and F tags", "Distances omit tagged transport legs"],
            "source_hashes": hashes, "traces": traces, "candidates": candidates,
            "findings": grouped_findings(candidates, parameters.near)}


def render(result, limit=20):
    lines = [f"{len(result['candidates'])} candidates; {len(result['findings'])} grouped findings. Units: {result['units']}."]
    for trace in result["traces"]:
        stats = trace["stats"]
        lines.append(f"{trace['profile_id']}: {stats.get('points', 0)} points; trace distance {stats['trace_distance']:.2f}; "
                     f"{stats.get('inferred_steps', 0)} database-located steps; "
                     f"{stats.get('gap_legs', 0)} gap legs; {stats.get('transport_steps', 0)} transport steps.")
    for number, finding in enumerate(result["findings"][:limit], 1):
        best = max(finding["occurrences"], key=lambda item: item["saving"] or 0)
        saving = f"{finding['max_saving']:.2f}" if finding["max_saving"] is not None else "unknown"
        classes = sorted({p.split("-")[2] for p in finding["profiles"]})
        lines.append(f"\n{number}. {finding['kind']} {finding['direction'] or ''} | {finding['zone']} | "
                     f"{','.join(classes)} | {len(finding['occurrences'])} occurrences | max geometric saving {saving} | "
                     f"{','.join(finding['uncertainty']) or 'continuous geometry'}")
        for ref in [best["source"], *best.get("leg_sources", [best.get("earlier_source", best["source"])])]:
            lines.append(f"  {ref['file']}:{ref['line']} {ref['text']}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Manifest or single guide file")
    parser.add_argument("--config", type=Path, default=ROOT / "CONFIGURATION.md")
    parser.add_argument("--race", required=True)
    parser.add_argument("--class", dest="cls")
    parser.add_argument("--faction")
    parser.add_argument('--questiedb', type=Path, help='Baked QuestieDB TOC; defaults to the matching sibling addon')
    for name, default in asdict(Parameters()).items():
        if name != "include_gaps":
            parser.add_argument("--" + name, type=float, default=default)
    parser.add_argument("--include-gaps", action="store_true", help="Also consider passage estimates involving unresolved steps")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", type=Path, help="Save full JSON and a sibling .txt summary")
    args = parser.parse_args(argv)
    try:
        parameters = Parameters(**{name: getattr(args, name) for name in asdict(Parameters())})
        parameters.check()
        if args.limit < 1:
            raise ValueError("Report limit must be positive")
        profiles = [p for p in profiles_from_configuration(args.config)
                    if p.race.casefold() == args.race.replace(" ", "").casefold()
                    and (not args.cls or p.cls.casefold() == args.cls.casefold())
                    and (not args.faction or p.faction.casefold() == args.faction.casefold())]
        if not profiles:
            raise ValueError("No configured profiles match the selection")
        if args.input.suffix == ".toc":
            parsed = validate_manifest(args.input)
            if parsed.diagnostics:
                raise ValueError("\n".join(map(str, parsed.diagnostics)))
            guides = parsed.guides
        else:
            guide = read_guide(args.input)
            errors = validate_guide(guide)
            if errors:
                raise ValueError("\n".join(map(str, errors)))
            guides = [guide]
        toc = args.questiedb
        if toc is None:
            manifest = args.input if args.input.suffix == '.toc' else next(ROOT.glob('*.toc'))
            flavor = manifest.stem.rsplit('_', 1)[-1]
            toc = ROOT.parent / 'QuestieDB' / f'QuestieDB_{flavor}.toc'
        database = QuestieDB(toc)
        result = audit(guides, profiles, parameters, database)
        summary = render(result, args.limit)
        if args.output:
            if args.output.suffix != ".json":
                raise ValueError("Output path must end in .json")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            args.output.with_suffix(".txt").write_text(summary, encoding="utf-8")
        print(summary, end="")
        return 0
    except (ValueError, UnicodeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    sys.exit(main())
