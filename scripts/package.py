#!/usr/bin/env python3
"""Prepare a plugin release: check the version, build the archive, drop a .zip
   copy (the claude.ai skill upload wants that extension) and extract the release
   notes from the CHANGELOG. Usable by hand as well as from CI.

   usage: scripts/package.py <name> [expected version]
"""
import json, pathlib, shutil, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent

def fail(msg):
    sys.exit(f"FAIL: {msg}")

if not 2 <= len(sys.argv) <= 3:
    fail("usage: scripts/package.py <name> [expected version]")
name, expected = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)

plugin_dir = root / "plugins" / name
if not plugin_dir.is_dir():
    fail(f"no plugin {name!r} under plugins/")

manifest = plugin_dir / ".claude-plugin" / "plugin.json"
if not manifest.exists():
    fail(f"{manifest.relative_to(root)} missing: nothing to publish")
version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
if not version:
    fail("plugin.json has no version field")
if expected and expected != version:
    fail(f"the tag says {expected} but plugin.json says {version}")

build = plugin_dir / "scripts" / "build.sh"
if not build.exists():
    fail(f"{build.relative_to(root)} missing: a publishable plugin must know how to build")
subprocess.run(["bash", str(build)], cwd=plugin_dir, check=True)

artifact = plugin_dir / f"{name}.skill"
if not artifact.exists():
    fail(f"build.sh did not produce {artifact.name}")

dist = root / "dist"
shutil.rmtree(dist, ignore_errors=True)
dist.mkdir()
shutil.copy2(artifact, dist / f"{name}.skill")
shutil.copy2(artifact, dist / f"{name}.zip")

# notes: the CHANGELOG section carrying this version, otherwise a generic line
notes = f"Version {version} of `{name}`."
changelog = plugin_dir / "CHANGELOG.md"
if changelog.exists():
    block = []
    for line in changelog.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if block:
                break
            if not line[3:].lstrip().startswith(version):
                continue
        if block or line.startswith("## "):
            block.append(line)
    if block:
        notes = "\n".join(block).strip()
(dist / "notes.md").write_text(notes + "\n", encoding="utf-8")
(dist / "version.txt").write_text(version + "\n", encoding="utf-8")

print(f"{name} {version} — dist/{name}.skill, dist/{name}.zip, dist/notes.md")
print(f"notes: {len(notes.splitlines())} lines")
