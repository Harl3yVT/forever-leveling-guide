#!/usr/bin/env python3
"""Validate a guide manifest (Python 3.10+).

Usage: python3 tools/validate.py [manifest.toc]
Defaults to the only TOC beside tools/.
Exit codes: 0 valid within supported checks; 1 validation/input error; 2 CLI error.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import sys

try:
    from .guide_parser import Diagnostic, Guide, ParseError, SourceLocation, read_guide, validate_guide
except ImportError:  # Direct execution: python3 tools/validate.py
    from guide_parser import Diagnostic, Guide, ParseError, SourceLocation, read_guide, validate_guide


@dataclass(frozen=True)
class ValidationResult:
    files: int
    guides: tuple[Guide, ...]
    diagnostics: tuple[Diagnostic, ...]


def validate_manifest(path: str | Path) -> ValidationResult:
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
            if tag.code == "NX" and tag.value not in seen_names:
                diagnostics.append(Diagnostic(tag.location, "reference",
                    f"Next guide {tag.value!r} does not exactly match a loaded [N name]"))
    if not seen_paths:
        error(1, "manifest", "Manifest lists no supported guide files")
    return ValidationResult(files, tuple(guides), tuple(diagnostics))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="Guide manifest (.toc)")
    args = parser.parse_args(argv)
    path = args.manifest
    if path is None:
        candidates = sorted(Path(__file__).resolve().parents[1].glob("*.toc"))
        if len(candidates) != 1:
            parser.error("Specify a manifest; expected exactly one TOC beside tools/")
        path = candidates[0]
    result = validate_manifest(path)
    for diagnostic in result.diagnostics:
        print(diagnostic, file=sys.stderr)
    steps = sum(len(guide.steps) for guide in result.guides)
    print(f"Checked {result.files} files / {len(result.guides)} guides / {steps} action or text steps; "
          f"{len(result.diagnostics)} errors.")
    return 1 if result.diagnostics else 0


if __name__ == "__main__":
    sys.exit(main())
