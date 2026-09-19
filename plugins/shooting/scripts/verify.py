#!/usr/bin/env python3
"""Pre-publication checks: plugin manifests, every skill's frontmatter, and the
   syntax and commands of the target-analysis engine."""
import ast, json, pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent
ENGINE_SKILL = "target-analysis"          # the only skill shipping an engine so far
errors = []

skills_dir = root / "skills"
skills = sorted(d for d in skills_dir.iterdir() if d.is_dir()) if skills_dir.is_dir() else []
if not skills:
    errors.append("no skill under skills/: nothing would be discovered")

# generic: every skill needs frontmatter, and its name must be its directory name
for skill in skills:
    card = skill / "SKILL.md"
    if not card.exists():
        errors.append(f"{skill.name}/SKILL.md missing: the directory is not a skill")
        continue
    md = card.read_text(encoding="utf-8")
    if not md.startswith("---\n"):
        errors.append(f"{skill.name}: no YAML frontmatter at the top of SKILL.md")
        continue
    head = md.split("---", 2)[1]
    for field in ("name:", "description:"):
        if field not in head:
            errors.append(f"{skill.name}: field {field} missing from frontmatter")
    if f"name: {skill.name}\n" not in head:
        errors.append(f"{skill.name}: frontmatter name must match the directory name, "
                      "otherwise the import creates a second skill")
    if "```python" in md:
        errors.append(f"{skill.name}: python block in SKILL.md, the engine belongs in scripts/")

# specific: the engine ships next to its skill, it is the source, nothing is transcribed
engine = skills_dir / ENGINE_SKILL / "scripts" / "cible.py"
if not engine.exists():
    errors.append(f"{engine} missing: the skill points at an engine that does not exist")
else:
    code = engine.read_text(encoding="utf-8")
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"cible.py syntax: line {e.lineno} — {e.msg}")
    for cmd in ("analyse", "overlay", "zoom", "tiles"):
        if f'"{cmd}"' not in code:
            errors.append(f"command {cmd} missing from cible.py")

# manifests: the name must agree everywhere, otherwise installation breaks
manifest = root / ".claude-plugin" / "plugin.json"
try:
    plugin = json.loads(manifest.read_text(encoding="utf-8"))
except FileNotFoundError:
    plugin = None
    errors.append(f"{manifest} missing: the plugin will not be installable")
except json.JSONDecodeError as e:
    plugin = None
    errors.append(f"unreadable plugin.json: {e}")
if plugin is not None and plugin.get("name") != root.name:
    errors.append(f"plugin.json name={plugin.get('name')!r} != directory {root.name!r}")

market = root.parent.parent / ".claude-plugin" / "marketplace.json"
if market.exists():
    entries = json.loads(market.read_text(encoding="utf-8")).get("plugins", [])
    src = f"./{root.relative_to(root.parent.parent).as_posix()}"
    if not any(e.get("source") == src for e in entries):
        errors.append(f"no marketplace.json entry points at {src}")
else:
    errors.append(f"{market} missing: the marketplace will list nothing")

if errors:
    print("\n".join("FAIL: " + e for e in errors))
    sys.exit(1)
print(f"OK — manifests, {len(skills)} skill(s), engine and commands")
