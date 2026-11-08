#!/usr/bin/env python3
"""Build a release ZIP from the manifest, documentation and authoring tools.

Usage: python3 tools/package.py [manifest.toc]
Defaults to the only TOC in the addon folder. Validation is a separate step.
"""
import argparse
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
INCLUDED_FILES = (
    'README.md', 'NEWS.md', 'AGENTS.md', 'CONFIGURATION.md', 'PLAYSTYLE.md', 'LEVELS.md',
    'LICENSE', 'Guidelime_Bethink.tga',
    'tools/guide_parser.py', 'tools/validate.py', 'tools/xp_budget.py',
    'tools/hub.py', 'tools/zone.py', 'tools/questie.py', 'tools/package.py',
)
GUIDE_PATTERN = 'guides/*.lua'


def read_source(root, name, included):
    relative = PurePosixPath(str(name).replace('\\', '/'))
    if relative.as_posix() not in included:
        raise ValueError(f'File is not in the inclusion list: {name}')
    path = root.joinpath(*relative.parts)
    try:
        resolved = path.resolve().relative_to(root)
    except ValueError:
        raise ValueError(f'File is outside the addon folder: {name}') from None
    if resolved != relative:
        raise ValueError(f'Included file must resolve to its listed path: {name}')
    if not path.is_file():
        raise ValueError(f'Missing included file: {name}')
    return relative, path.read_bytes()


def build_package(root, manifest=None):
    root = root.resolve()
    if manifest is None:
        manifests = sorted(root.glob('*.toc'))
        if len(manifests) != 1:
            raise ValueError('Specify a manifest when the addon folder does not contain exactly one TOC.')
        manifest = manifests[0]
    manifest = Path(manifest)
    if manifest.is_absolute():
        manifest = manifest.relative_to(root)
    if len(manifest.parts) != 1 or manifest.suffix != '.toc':
        raise ValueError('The manifest must be a TOC in the addon folder.')
    if not (manifest.stem == root.name or manifest.stem.startswith(root.name + '_')):
        raise ValueError('The manifest name must match the top-level addon folder name.')
    guide_names = {path.relative_to(root).as_posix() for path in root.glob(GUIDE_PATTERN)}
    if not guide_names:
        raise ValueError(f'No guide files match {GUIDE_PATTERN}')
    included = set(INCLUDED_FILES) | guide_names | {manifest.as_posix()}
    manifest_name, manifest_data = read_source(root, manifest, included)
    text = manifest_data.decode('utf-8-sig')
    match = re.search(r'^##\s*Version:\s*([^\r\n]+)', text, re.MULTILINE)
    version = match.group(1).strip() if match else ''
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', version):
        raise ValueError('The manifest needs a Version containing letters, digits, dots, hyphens, underscores or plus signs.')
    load_files = [line.strip() for line in text.splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
    if not load_files:
        raise ValueError('The manifest does not list any files to load.')
    for name in load_files:
        relative = PurePosixPath(name.replace('\\', '/'))
        if relative.as_posix() not in guide_names:
            raise ValueError(f'Manifest entry is not an included guide: {name}')

    files = dict(read_source(root, name, included) for name in sorted(included))
    files[manifest_name] = manifest_data

    output_dir = root / 'dist'
    output_dir.mkdir(exist_ok=True)
    output = output_dir / f'{root.name}-{version}.zip'
    with tempfile.TemporaryDirectory(prefix='.package-', dir=output_dir) as staging:
        temporary = Path(staging) / output.name
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in sorted(files, key=str):
                entry = zipfile.ZipInfo(f'{root.name}/{relative.as_posix()}')
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, files[relative])
        temporary.replace(output)
    return output, len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('manifest', nargs='?', type=Path, help='Defaults to the only TOC in the addon folder')
    args = parser.parse_args()
    try:
        output, count = build_package(ROOT, args.manifest)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Packaging failed: {error}\n')
    print(f'Created {output} ({count} files, {output.stat().st_size:,} bytes).')


if __name__ == '__main__':
    main()
