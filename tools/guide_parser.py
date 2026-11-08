"""Parser for the guide notation supported by this pack.

Public API: parse_guide(text), read_guide(path), and validate_guide(guide).
Parsing returns one immutable, source-located Guide;
malformed or unsupported syntax raises ParseError. Structural validation returns
Diagnostic objects.

parse_guide accepts guide text directly. read_guide extracts exactly one
long-bracket text block from a UTF-8 file, retaining original source locations.
Delimiters may contain matching equals signs. Comments and quoted strings are
skipped during extraction; surrounding file syntax is outside guide validation.

Supported tags: N D GA NX A G L QA QC QT CI UI TAR XP SK SP LE LESP F P H S O OC T V R.
Locations require an explicit zone; quest locations are never inferred. G also
accepts an optional comma-separated radius. Numeric suffixes are retained as
notation, without simulating completion. Unknown tags/conditions are errors.
Names of maps, flight points, skills and referenced game entities are not checked
against a database. Applicability is represented, not evaluated against a player.
"""

from bisect import bisect_right
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re


@dataclass(frozen=True)
class SourceLocation:
    path: str
    line: int
    column: int

    def __str__(self):
        return f"{self.path}:{self.line}:{self.column}"


@dataclass(frozen=True)
class Diagnostic:
    location: SourceLocation
    code: str
    message: str

    def __str__(self):
        return f"{self.location}: {self.code}: {self.message}"


class ParseError(ValueError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__(str(diagnostic))


@dataclass(frozen=True)
class Condition:
    kind: str
    name: str
    operator: str | None = None
    value: int | None = None


@dataclass(frozen=True)
class Applicability:
    # Preserve term order and categories; do not guess a player's dynamic state.
    conditions: tuple[Condition, ...]


@dataclass(frozen=True)
class Coordinates:
    x: float
    y: float
    zone: str
    radius: float | None = None


@dataclass(frozen=True)
class QuestReference:
    quest_id: int
    objectives: tuple[int, ...] = ()
    title: str | None = None


@dataclass(frozen=True)
class ItemReference:
    item_id: int
    quantity: int = 1
    suffix: str = ""


@dataclass(frozen=True)
class TargetReference:
    npc_id: int
    suffix: str = ""


@dataclass(frozen=True)
class SkillReference:
    name: str
    rank: int
    suffix: str = ""

    @property
    def is_profession(self):
        return _CONDITION_KINDS.get(self.name) == "profession"


@dataclass(frozen=True)
class SpellReference:
    spell_id: int
    rank: int = 1
    suffix: str = ""


@dataclass(frozen=True)
class Text:
    text: str
    location: SourceLocation


@dataclass(frozen=True)
class Tag:
    code: str
    argument: str
    value: (str | int | None | Applicability | Coordinates | QuestReference
            | ItemReference | TargetReference | SkillReference | SpellReference)
    raw: str
    location: SourceLocation


@dataclass(frozen=True)
class Step:
    raw: str
    elements: tuple[Text | Tag, ...]
    location: SourceLocation

    @property
    def tags(self):
        return tuple(e for e in self.elements if isinstance(e, Tag))

    @property
    def is_header(self):
        return any(tag.code in HEADER_TAGS for tag in self.tags)


@dataclass(frozen=True)
class Guide:
    lines: tuple[Step, ...]  # All nonblank source lines, including metadata.
    location: SourceLocation

    @property
    def headers(self):
        return tuple(tag for line in self.lines for tag in line.tags
                     if tag.code in HEADER_TAGS)

    @property
    def name(self):
        return next((tag.value for tag in self.headers if tag.code == "N"), None)

    @property
    def description(self):
        return next((tag.value for tag in self.headers if tag.code == "D"), None)

    @property
    def applicability(self):
        return next((tag.value for tag in self.headers if tag.code == "GA"), None)

    @property
    def next_guides(self):
        return tuple(tag.value for tag in self.headers if tag.code == "NX")

    @property
    def steps(self):
        return tuple(line for line in self.lines if not line.is_header)


HEADER_TAGS = frozenset({"N", "D", "GA", "NX"})
FLAG_TAGS = frozenset({"O", "OC", "T", "V", "R"})
PLACE_TAGS = frozenset({"F", "P", "H", "S"})
SUPPORTED_TAGS = (HEADER_TAGS | FLAG_TAGS | PLACE_TAGS
                  | {"A", "G", "L", "QA", "QC", "QT", "CI", "UI", "TAR",
                     "XP", "SK", "SP", "LE", "LESP"})

# Vocabulary of the supported notation. No routing or
# quest behavior depends on individual names. Extend explicitly for new flavors.
_NAMES = {
    "class": "Druid Hunter Mage Paladin Priest Rogue Shaman Warlock Warrior".split(),
    "race": "Human Dwarf Gnome NightElf Orc Troll Tauren Undead Skyborne".split(),
    "faction": ["Alliance", "Horde"],
    "mode": ["Hardcore", "Softcore"],
    "profession": ["Alchemy", "Blacksmithing", "Enchanting", "Engineering", "Herbalism",
                   "Leatherworking", "Mining", "Skinning", "Tailoring", "First Aid",
                   "Cooking", "Fishing"],
}
_CONDITION_KINDS = {name: kind for kind, names in _NAMES.items() for name in names}
_NUMBER = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
_LONG_OPEN = re.compile(r"\[(=*)\[")
_TEXT_TOKEN = re.compile(r"--|[\"']|\[(=*)\[")
_QUOTED_TEXT = re.compile(r"'(?:\\[\s\S]|[^'\\])*'" r'|"(?:\\[\s\S]|[^"\\])*"')


class _Source:
    def __init__(self, text, path):
        self.text = text
        self.path = str(path)
        self.starts = [0] + [m.end() for m in re.finditer(r"\r\n|\r|\n", text)]

    def location(self, offset):
        line = bisect_right(self.starts, offset) - 1
        return SourceLocation(self.path, line + 1, offset - self.starts[line] + 1)

    def fail(self, offset, message, code="syntax"):
        raise ParseError(Diagnostic(self.location(offset), code, message))


def _require_match(pattern, argument, source, offset, expected):
    match = re.fullmatch(pattern, argument)
    if match is None:
        source.fail(offset, f"Expected {expected}; got {argument!r}")
    return match


def _integer(text, source, offset):
    try:
        return int(text)
    except ValueError:
        source.fail(offset, "Integer exceeds Python's supported conversion limit")


def _applicability(argument, source, offset):
    terms = []
    for term in argument.split(","):
        term = term.strip()
        match = re.fullmatch(r"(.+?)(?:(<=|>=|<|>|=)([0-9]+))?", term)
        if match is None:
            source.fail(offset, "Expected comma-separated applicability conditions")
        name, operator, value = match.groups()
        if re.fullmatch(r"IT[0-9]+", name):
            kind = "item"
            if _integer(name[2:], source, offset) < 1 or operator is None:
                source.fail(offset, "Item conditions require a positive ID and a comparison")
        else:
            kind = _CONDITION_KINDS.get(name)
            if kind is None:
                source.fail(offset, f"Unsupported applicability name {name!r}", "unsupported")
            if operator is not None and kind != "profession":
                source.fail(offset, "Only profession and item conditions accept numeric comparisons")
        terms.append(Condition(kind, name, operator, _integer(value, source, offset) if value else None))
    return Applicability(tuple(terms))


def _tag(raw, source, offset):
    match = re.fullmatch(r"\[([A-Z]+)([^\[\]]*)\]", raw)
    if match is None:
        source.fail(offset, "Expected an uppercase tag code and a closing bracket")
    code, tail = match.groups()
    if code not in SUPPORTED_TAGS:
        source.fail(offset, f"Unsupported tag [{code}]", "unsupported")
    argument = tail.strip()
    if code in FLAG_TAGS:
        if argument:
            source.fail(offset, f"[{code}] does not accept arguments")
        value = None
    else:
        if not argument:
            source.fail(offset, f"[{code}] requires an argument")
        if code in HEADER_TAGS | PLACE_TAGS | {"A", "SK", "LE"} and not tail[0].isspace():
            source.fail(offset, f"Expected whitespace after {code}")
        if code in {"N", "D", "NX"} | PLACE_TAGS:
            value = argument
        elif code in {"A", "GA"}:
            value = _applicability(argument, source, offset)
        elif code in {"G", "L"}:
            radius = rf"(?:\s*,\s*({_NUMBER}))?" if code == "G" else ""
            match = _require_match(
                rf"({_NUMBER})\s*,\s*({_NUMBER}){radius}\s+([^\r\n]+)",
                argument, source, offset, "x,y zone (G optionally accepts x,y,radius zone)")
            groups = match.groups()
            value = Coordinates(float(groups[0]), float(groups[1]), groups[-1].strip(),
                                float(groups[2]) if code == "G" and groups[2] else None)
        elif code in {"QA", "QC", "QT"}:
            indices = r"(?:\s*,\s*[0-9]+)*" if code == "QC" else ""
            match = _require_match(rf"([0-9]+{indices})(?:\s+(.+))?", argument, source, offset,
                                   "a quest ID, optional QC objective indices, and optional title")
            numbers = tuple(_integer(n.strip(), source, offset) for n in match[1].split(","))
            value = QuestReference(numbers[0], numbers[1:], match[2])
        elif code == "CI":
            match = _require_match(r"([0-9]+)(?:\s*,\s*([0-9]+)(-?))?", argument,
                                   source, offset, "itemID[,quantity[-]]")
            item, count, suffix = match.groups()
            value = ItemReference(_integer(item, source, offset),
                                  _integer(count, source, offset) if count else 1, suffix or "")
        elif code in {"UI", "LESP", "XP"}:
            _require_match(r"[0-9]+", argument, source, offset, "a positive integer")
            number = _integer(argument, source, offset)
            value = (ItemReference(number) if code == "UI" else
                     SpellReference(number) if code == "LESP" else number)
        elif code == "TAR":
            match = _require_match(r"([0-9]+)(-?)", argument, source, offset, "npcID[-]")
            value = TargetReference(_integer(match[1], source, offset), match[2])
        elif code == "SP":
            match = _require_match(r"([0-9]+)(-?)", argument, source, offset, "spellID[-]")
            value = SpellReference(_integer(match[1], source, offset), suffix=match[2])
        elif code in {"SK", "LE"}:
            match = _require_match(r"([A-Za-z][A-Za-z0-9 ']*?)\s+([0-9]+)(-?)", argument,
                                   source, offset, "skill rank[-] or LE SPspellID rank[-]")
            name, rank, suffix = match.groups()
            if name.startswith("SP") and re.fullmatch(r"SP[0-9]+", name):
                if code != "LE":
                    source.fail(offset, "Spell checks use LE or LESP")
                value = SpellReference(_integer(name[2:], source, offset),
                                       _integer(rank, source, offset), suffix)
            else:
                value = SkillReference(name, _integer(rank, source, offset), suffix)
    return Tag(code, argument, value, raw, source.location(offset))


def _body(source, begin, end):
    lines = []
    offset = begin
    for chunk in source.text[begin:end].splitlines(keepends=True):
        raw = chunk.rstrip("\r\n")
        if raw.strip():
            elements = []
            cursor = 0
            while cursor < len(raw):
                opening = raw.find("[", cursor)
                closing = raw.find("]", cursor)
                if closing != -1 and (opening == -1 or closing < opening):
                    source.fail(offset + closing, "Unmatched closing bracket")
                if opening == -1:
                    elements.append(Text(raw[cursor:], source.location(offset + cursor)))
                    break
                if opening > cursor:
                    elements.append(Text(raw[cursor:opening], source.location(offset + cursor)))
                closing = raw.find("]", opening)
                if closing == -1:
                    source.fail(offset + opening, "Unterminated tag")
                elements.append(_tag(raw[opening:closing + 1], source, offset + opening))
                cursor = closing + 1
            lines.append(Step(raw, tuple(elements), source.location(offset)))
        offset += len(chunk)
    return Guide(tuple(lines), source.location(begin))


def parse_guide(text: str, *, source: str = "<string>") -> Guide:
    """Parse guide text. Call validate_guide separately for structural checks."""
    return _body(_Source(text, source), 0, len(text))


def _block_bounds(source, opening):
    closing = "]" + opening[1] + "]"
    end = source.text.find(closing, opening.end())
    if end == -1:
        source.fail(opening.start(), "Unterminated text block", "extraction")
    return opening.end(), end, end + len(closing)


def _extract_text(source):
    position, bounds = 0, None
    while token := _TEXT_TOKEN.search(source.text, position):
        position = token.end()
        if token[0] == "--":
            comment = _LONG_OPEN.match(source.text, position)
            if comment:
                _, _, position = _block_bounds(source, comment)
            else:
                newline = re.search(r"[\r\n]", source.text[position:])
                position = position + newline.end() if newline else len(source.text)
        elif token[0] in {"'", '"'}:
            quoted = _QUOTED_TEXT.match(source.text, token.start())
            if quoted:
                position = quoted.end()
        else:
            begin, end, position = _block_bounds(source, token)
            if bounds is not None:
                source.fail(token.start(), "Expected one guide text block per file", "extraction")
            bounds = begin, end
    if bounds is None:
        source.fail(0, "Expected one guide text block per file", "extraction")
    return bounds


def read_guide(path: str | Path) -> Guide:
    """Extract and parse one guide from a UTF-8 file. File errors propagate."""
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        source = _Source(stream.read(), path)
    begin, end = _extract_text(source)
    return _body(source, begin, end)


def validate_guide(guide: Guide) -> tuple[Diagnostic, ...]:
    """Check supported structural rules; never resolve locations or simulate play."""
    diagnostics = []

    def error(location, code, message):
        diagnostics.append(Diagnostic(location, code, message))

    headers = guide.headers
    for code in ("N", "D", "GA"):
        found = [tag for tag in headers if tag.code == code]
        if code == "N" and not found:
            error(guide.location, "metadata", "Guide requires one [N name] tag")
        for tag in found[1:]:
            error(tag.location, "metadata", f"Duplicate [{code}] metadata")
    if not guide.steps:
        error(guide.location, "structure", "Guide has no action or text steps")
    seen_action = False
    for line in guide.lines:
        if line.is_header:
            if seen_action:
                error(line.location, "metadata", "Guide metadata must precede action steps")
            if any(tag.code not in HEADER_TAGS for tag in line.tags) or any(
                    isinstance(e, Text) and e.text.strip() for e in line.elements):
                error(line.location, "metadata", "Metadata lines cannot contain actions or surrounding prose")
        else:
            seen_action = True
        for tag in line.tags:
            value = tag.value
            if tag.code in {"N", "NX"}:
                levels = re.match(r"^([0-9]+)-([0-9]+)(?:\s|$)", tag.argument)
                if levels:
                    try:
                        start, end = int(levels[1]), int(levels[2])
                    except ValueError:
                        error(tag.location, "metadata", "Level range exceeds Python's supported conversion limit")
                    else:
                        if start < 1 or end < start or not tag.argument[levels.end():].strip():
                            error(tag.location, "metadata", "Expected a positive, ascending level range followed by a title")
            if isinstance(value, Coordinates):
                if not all(isfinite(n) and 0 <= n <= 100 for n in (value.x, value.y)):
                    error(tag.location, "coordinates", "Coordinates must be finite numbers between 0 and 100")
                if value.radius is not None and (not isfinite(value.radius) or value.radius < 0):
                    error(tag.location, "coordinates", "Radius must be finite and nonnegative")
            if isinstance(value, QuestReference) and (value.quest_id < 1 or any(n < 1 for n in value.objectives)):
                error(tag.location, "reference", "Quest IDs and objective indices must be positive")
            if isinstance(value, ItemReference) and (value.item_id < 1 or value.quantity < 1):
                error(tag.location, "reference", "Item IDs and quantities must be positive")
            if isinstance(value, TargetReference) and value.npc_id < 1:
                error(tag.location, "reference", "NPC IDs must be positive")
            if isinstance(value, SpellReference) and (value.spell_id < 1 or value.rank < 1):
                error(tag.location, "reference", "Spell IDs and ranks must be positive")
            if isinstance(value, SkillReference) and value.rank < 1:
                error(tag.location, "reference", "Skill ranks must be positive")
            if tag.code == "XP" and value < 1:
                error(tag.location, "reference", "Level must be positive")
    return tuple(diagnostics)
