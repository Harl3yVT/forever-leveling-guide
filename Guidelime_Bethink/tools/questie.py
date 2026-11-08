"""Read QuestieDB's baked TOC metadata.

QuestieDB(toc) returns named records and candidate locations with AreaTable IDs.
"""

import base64
import binascii
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path
import re
import struct


def decode_cbor(data):
    """Decode the definite-length CBOR values used by QuestieDB's metadata."""
    offset = 0

    def take(size):
        nonlocal offset
        end = offset + size
        if end > len(data):
            raise ValueError("Truncated QuestieDB CBOR value")
        result = data[offset:end]
        offset = end
        return result

    def value():
        head = take(1)[0]
        major, extra = head >> 5, head & 31
        if major == 7:
            if extra in (20, 21):
                return extra == 21
            if extra in (22, 23):
                return None
            if extra in (25, 26, 27):
                return struct.unpack({25: '>e', 26: '>f', 27: '>d'}[extra],
                                     take(1 << (extra - 24)))[0]
            raise ValueError("Unsupported QuestieDB CBOR simple value")
        if extra < 24:
            size = extra
        elif extra < 28:
            size = int.from_bytes(take(1 << (extra - 24)), 'big')
        else:
            raise ValueError("Unsupported indefinite-length QuestieDB CBOR value")
        if major == 0:
            return size
        if major == 1:
            return -1 - size
        if major in (2, 3):
            # QuestieDB stores UTF-8 names in CBOR byte strings as well as text.
            return take(size).decode('utf-8')
        if major == 4:
            return [value() for _ in range(size)]
        if major == 5:
            result = {}
            for _ in range(size):
                key = value()
                result[key] = value()
            return result
        if major == 6:
            return value()
        raise ValueError("Unsupported QuestieDB CBOR value")

    result = value()
    if offset != len(data):
        raise ValueError("Trailing data in QuestieDB CBOR value")
    return result


def table_items(value):
    """Lua integer-keyed tables may be encoded as either CBOR maps or arrays."""
    if isinstance(value, dict):
        return value.items()
    return enumerate(value, 1) if isinstance(value, list) else ()


def slot(value, index, default=None):
    if isinstance(value, dict):
        return value.get(index, default)
    return value[index - 1] if isinstance(value, list) and len(value) >= index else default


def zone_key(name):
    return re.sub(r'[^a-z0-9]', '', name.casefold())


@dataclass(frozen=True)
class Location:
    area_id: int
    x: float
    y: float
    entity: str
    entity_id: int


class QuestieDB:
    def __init__(self, toc):
        self.path = Path(toc).resolve()
        text = self.path.read_text(encoding='utf-8-sig')
        self.metadata = dict(re.findall(r'^##\s*([^:\r\n]+):\s*([^\r\n]*)', text, re.M))
        if self.metadata.get('X-Mode') != 'baked':
            raise ValueError(f"Expected a baked QuestieDB TOC: {self.path}")
        if self.metadata.get('X-Contract-Version') != '4':
            raise ValueError(f"Unsupported QuestieDB contract: {self.metadata.get('X-Contract-Version')}")
        self.fields = {}
        for entity in ('Quest', 'Npc', 'Item', 'Object'):
            schema = self.path.parent / 'src' / 'meta' / f'{entity.lower()}Meta.lua'
            self.fields[entity] = {int(number): name for name, number in
                                   re.findall(r"\['([^']+)'\]\s*=\s*(\d+)", schema.read_text())}
            if not self.fields[entity]:
                raise ValueError(f"Missing QuestieDB field schema: {schema}")
        zones = self.path.parent / 'src' / 'corrections' / 'enum' / 'zones.lua'
        self.zone_names = {int(number): name.replace('_', ' ').title() for name, number in
                           re.findall(r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)', zones.read_text(), re.M)}
        self.zone_ids = {zone_key(name): ident for ident, name in self.zone_names.items()}

    def zone_id(self, name):
        return self.zone_ids.get(zone_key(name))

    def _stored(self, key):
        encoded = self.metadata.get(key)
        if encoded is None:
            return None
        chunks = re.fullmatch(r'~(\d+)~', encoded)
        if chunks:
            try:
                encoded = ''.join(self.metadata[f'{key}-{i}'] for i in range(1, int(chunks[1]) + 1))
            except KeyError as exc:
                raise ValueError(f"Missing QuestieDB metadata chunk: {exc.args[0]}") from None
        try:
            return decode_cbor(base64.b64decode(encoded, validate=True))
        except (ValueError, binascii.Error, UnicodeError) as exc:
            raise ValueError(f"Invalid QuestieDB metadata {key}: {exc}") from exc

    @lru_cache(maxsize=None)
    def _record(self, entity, ident):
        if entity not in self.fields:
            raise ValueError(f"Unknown QuestieDB entity type: {entity}")
        prefix = f'X-{entity}-{ident}-'
        scalar = self._stored(prefix + 'S')
        if scalar is None:
            return {}
        result = {self.fields[entity][index]: item for index, item in table_items(scalar)
                  if index in self.fields[entity] and item is not None}
        for index, name in self.fields[entity].items():
            item = self._stored(prefix + str(index))
            if item is not None:
                result[name] = item
        return result

    def record(self, entity, ident):
        """Return a fresh named record; an unknown ID returns an empty dictionary."""
        return deepcopy(self._record(entity, ident))

    @staticmethod
    def spawn_locations(spawns, entity, ident):
        result = []
        for area, rows in table_items(spawns):
            for _, row in table_items(rows):
                x, y = slot(row, 1), slot(row, 2)
                if (isinstance(x, (int, float)) and isinstance(y, (int, float))
                        and isfinite(x) and isfinite(y) and 0 <= x <= 100 and 0 <= y <= 100):
                    result.append(Location(int(area), x, y, entity, ident))
        return tuple(dict.fromkeys(result))

    @lru_cache(maxsize=None)
    def locations(self, entity, ident):
        return self.spawn_locations(self._record(entity, ident).get('spawns'), entity, ident)

    def item_locations(self, ident, npc_ids=(), _seen=frozenset()):
        """Follow drops/containers; an explicit NPC list restricts collection sources."""
        if ident in _seen:
            return ()
        item = self._record('Item', ident)
        result = []
        for field, entity in [('npcDrops', 'Npc'), ('objectDrops', 'Object')]:
            for _, source in table_items(item.get(field)):
                if npc_ids and (entity != 'Npc' or source not in npc_ids):
                    continue
                result.extend(self.locations(entity, source))
        for _, container in table_items(item.get('itemDrops')):
            result.extend(self.item_locations(container, npc_ids, _seen | {ident}))
        return tuple(dict.fromkeys(result))

    def quest_locations(self, ident, kind, objectives=(), npc_ids=(), faction=None):
        """Return candidate locations grouped by quest objective.

        Objective indices follow creature, object, item, reputation, kill-credit,
        spell order. Empty groups indicate unresolved destinations.
        """
        quest = self._record('Quest', ident)
        if not quest:
            return ((),)
        if kind in ('QA', 'QT'):
            result = []
            groups = quest.get('startedBy' if kind == 'QA' else 'finishedBy')
            for group, entity in enumerate(('Npc', 'Object', 'Item'), 1):
                for _, source in table_items(slot(groups, group)):
                    if entity == 'Item':
                        result.extend(self.item_locations(source, npc_ids))
                    else:
                        record = self._record(entity, source)
                        friendly = record.get('friendlyToFaction')
                        if entity == 'Npc' and friendly and faction and faction[0] not in friendly:
                            continue
                        result.extend(self.locations(entity, source))
            return (tuple(dict.fromkeys(result)),)
        if kind != 'QC':
            raise ValueError(f"Unknown quest action: {kind}")
        groups = []
        for category in range(1, 7):
            rows = slot(quest.get('objectives'), category)
            if category == 4 and rows:
                groups.append(())  # Reputation has no destination in this data.
                continue
            for _, row in table_items(rows):
                target = slot(row, 1)
                if category == 3:
                    points = self.item_locations(target, npc_ids)
                elif category in (1, 2):
                    points = self.locations('Npc' if category == 1 else 'Object', target)
                    if npc_ids:
                        points = tuple(p for p in points if p.entity == 'Npc' and p.entity_id in npc_ids)
                elif category == 5:
                    points = tuple(p for _, source in table_items(target)
                                   if not npc_ids or source in npc_ids for p in self.locations('Npc', source))
                else:
                    points = ()
                groups.append(points)
        if objectives:
            return tuple(groups[i - 1] if 0 < i <= len(groups) else () for i in objectives)
        if not groups:
            trigger = slot(quest.get('triggerEnd'), 2)
            groups = [self.spawn_locations(trigger, 'Quest', ident)]
        return tuple(groups)
