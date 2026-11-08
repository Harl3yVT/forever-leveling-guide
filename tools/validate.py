#!/usr/bin/env python3
"""Validate a guide manifest (Python 3.10+).

Usage: python3 tools/validate.py [manifest.toc] [--check-training 2-42]
Defaults to Guidelime_HarleyMage/Guidelime_HarleyMage.toc in this repo.
Exit codes: 0 valid within supported checks; 1 validation/input error; 2 CLI error.

Optional training-coverage check (warnings only, never changes the exit code):
enable it with `## X-CheckTraining: 2-42` in the manifest or `--check-training 2-42`.
For every class named in an [A ...] filter on a [T] step, it warns about each even
level in the range with no [T] step for that class at that level or the level after.
A step's level is an explicit "level-N"/"level N"/"(N)" in its text, otherwise it is
interpolated from the chapter's [N A-B ...] range and its [XP N] markers by position.
Accepted gaps: `## X-CheckTraining-Allow: Mage:24,26; Priest:30` (class:levels; ...).
"""

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import sys

try:
    from .guide_parser import Applicability, Diagnostic, Guide, ParseError, SourceLocation, Text, read_guide, validate_guide
except ImportError:  # Direct execution: python3 tools/validate.py
    from guide_parser import Applicability, Diagnostic, Guide, ParseError, SourceLocation, Text, read_guide, validate_guide


@dataclass(frozen=True)
class ValidationResult:
    files: int
    guides: tuple[Guide, ...]
    diagnostics: tuple[Diagnostic, ...]


def validate_manifest(path: str | Path, other_names=frozenset()) -> ValidationResult:
    """Read one guide per manifest entry and aggregate diagnostics."""
    path = Path(path).resolve()
    diagnostics, guides = [], []
    files = 0

    def error(line, code, message):
        diagnostics.append(Diagnostic(SourceLocation(str(path), line, 1), code, message))

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        error(1, "input", str(exc))
        return ValidationResult(0, (), tuple(diagnostics))
    interfaces = [(n, match[1].strip()) for n, line in enumerate(lines, 1)
                  if (match := re.fullmatch(r"\s*##\s*Interface:\s*(.*)", line))]
    if len(interfaces) != 1:
        error(interfaces[-1][0] if interfaces else 1, "manifest", "Manifest requires exactly one Interface field")
    elif not re.fullmatch(r"[1-9][0-9]*(?:\s*,\s*[1-9][0-9]*)*", interfaces[0][1]):
        error(interfaces[0][0], "manifest", "Interface must contain positive, comma-separated build numbers")
    seen_paths, seen_names = set(), {}
    for number, raw in enumerate(lines, 1):
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        relative = PurePosixPath(name.replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or ":" in name or relative.suffix != ".lua":
            error(number, "manifest", "Expected a local .lua guide path without parent traversal")
            continue
        try:
            target = path.parent.joinpath(*relative.parts).resolve()
            target.relative_to(path.parent)
        except (OSError, ValueError, RuntimeError):
            error(number, "manifest", "Guide path resolves outside the manifest directory or cannot be resolved")
            continue
        if target in seen_paths:
            error(number, "manifest", f"Duplicate guide file {name!r}")
            continue
        seen_paths.add(target)
        files += 1
        try:
            guide = read_guide(target)
        except ParseError as exc:
            diagnostics.append(exc.diagnostic)
            continue
        except (OSError, UnicodeError) as exc:
            error(number, "input", f"Cannot read {name!r}: {exc}")
            continue
        diagnostics.extend(validate_guide(guide))
        if guide.name is not None:
            if guide.name in seen_names:
                diagnostics.append(Diagnostic(guide.location, "metadata",
                    f"Duplicate guide name {guide.name!r}; first at {seen_names[guide.name]}"))
            else:
                seen_names[guide.name] = guide.location
        guides.append(guide)
    for guide in guides:
        for tag in guide.headers:
            if tag.code == "NX" and tag.value not in seen_names and tag.value not in other_names:
                diagnostics.append(Diagnostic(tag.location, "reference",
                    f"Next guide {tag.value!r} does not exactly match a loaded [N name]"))
    if not seen_paths:
        error(1, "manifest", "Manifest lists no supported guide files")
    return ValidationResult(files, tuple(guides), tuple(diagnostics))


_LEVEL_TEXT = re.compile(r"\blevel[- ]([0-9]{1,2})\b|\(([0-9]{1,2})\)", re.I)


def _manifest_field(path, name):
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None
    match = re.search(rf"^\s*##\s*{re.escape(name)}:\s*(.*?)\s*$", text, re.M)
    return match[1] if match else None


def parse_level_range(text):
    match = re.fullmatch(r"\s*([0-9]+)\s*-\s*([0-9]+)\s*", text or "")
    if not match or int(match[1]) > int(match[2]):
        raise ValueError(f"Expected a level range such as 2-42, got {text!r}")
    return int(match[1]), int(match[2])


def parse_allow(text):
    allowed = {}
    for part in (text or "").split(";"):
        if ":" in part:
            name, levels = part.split(":", 1)
            allowed.setdefault(name.strip(), set()).update(
                int(n) for n in re.findall(r"[0-9]+", levels))
    return allowed


def training_steps(guide):
    """Yield (classes, level, step) for each class-filtered [T] step, with an inferred level."""
    match = re.match(r"([0-9]+)-([0-9]+)", guide.name or "")
    if not match:
        return
    start, end = int(match[1]), int(match[2])
    steps = guide.steps
    anchors = [(0, start)]
    for index, step in enumerate(steps):
        for tag in step.tags:
            if tag.code == "XP" and isinstance(tag.value, int):
                anchors.append((index, tag.value))
    anchors.append((len(steps), end))
    anchors.sort()

    def interpolate(index):
        for (i0, l0), (i1, l1) in zip(anchors, anchors[1:]):
            if i0 <= index <= i1:
                return l0 if i1 == i0 else l0 + (l1 - l0) * (index - i0) / (i1 - i0)
        return end

    for index, step in enumerate(steps):
        if not any(tag.code == "T" for tag in step.tags):
            continue
        classes = [c.name for tag in step.tags if tag.code == "A" and isinstance(tag.value, Applicability)
                   for c in tag.value.conditions if c.kind == "class"]
        if not classes:
            continue
        text = " ".join(e.text for e in step.elements if isinstance(e, Text))
        explicit = _LEVEL_TEXT.search(text)
        level = int(explicit[1] or explicit[2]) if explicit else int(interpolate(index) + 0.5)
        yield classes, level, step


def check_training(guides, level_range, allowed=None):
    """Return (warnings, allowed_gaps): lists of (class, level) gaps, sorted."""
    low, high = level_range
    found = {}
    for guide in guides:
        for classes, level, _ in training_steps(guide):
            for name in classes:
                found.setdefault(name, set()).add(level)
    allowed = allowed or {}
    warnings, accepted = [], []
    for name in sorted(found):
        for level in range(low + low % 2, high + 1, 2):
            if level in found[name] or level + 1 in found[name]:
                continue
            (accepted if level in allowed.get(name, ()) else warnings).append((name, level))
    return warnings, accepted


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="Guide manifest (.toc)")
    parser.add_argument("--check-training", metavar="A-B",
                        help="Warn about even levels A..B with no class [T] step (overrides X-CheckTraining)")
    args = parser.parse_args(argv)
    path = args.manifest
    if path is None:
        path = Path(__file__).resolve().parents[1] / "Guidelime_HarleyMage" / "Guidelime_HarleyMage.toc"
    other = set()
    bethink = sorted((Path(__file__).resolve().parents[1] / "Guidelime_Bethink").glob("*.toc"))
    if bethink and Path(path).resolve() != bethink[0].resolve():
        # chapters may hand off to Bethink's guides (another addon): accept those [NX] names
        other = {g.name for g in validate_manifest(bethink[0]).guides if g.name}
    result = validate_manifest(path, frozenset(other))
    for diagnostic in result.diagnostics:
        print(diagnostic, file=sys.stderr)
    steps = sum(len(guide.steps) for guide in result.guides)
    print(f"Checked {result.files} files / {len(result.guides)} guides / {steps} action or text steps; "
          f"{len(result.diagnostics)} errors.")
    level_text = args.check_training or _manifest_field(path, "X-CheckTraining")
    if level_text:
        try:
            level_range = parse_level_range(level_text)
        except ValueError as exc:
            parser.error(str(exc))
        warnings, accepted = check_training(result.guides, level_range,
                                            parse_allow(_manifest_field(path, "X-CheckTraining-Allow")))
        for name, level in warnings:
            print(f"warning: training: {name} has no [T] step at level {level} or {level + 1}")
        summary = {}
        for name, level in accepted:
            summary.setdefault(name, []).append(level)
        allowed_text = "; ".join(f"{n} {','.join(map(str, ls))}" for n, ls in summary.items())
        print(f"Training coverage {level_range[0]}-{level_range[1]}: {len(warnings)} warnings, "
              f"{len(accepted)} allowed gaps{' (' + allowed_text + ')' if allowed_text else ''}.")
    return 1 if result.diagnostics else 0


if __name__ == "__main__":
    sys.exit(main())
