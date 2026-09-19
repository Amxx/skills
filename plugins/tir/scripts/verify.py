#!/usr/bin/env python3
"""Pre-publication checks: plugin manifests, skill frontmatter, syntax of the
   shipped engine and presence of the expected commands."""
import ast, json, pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent
skill = root / "skills" / "tir"
md = (skill / "SKILL.md").read_text(encoding="utf-8")
errors = []

if not md.startswith("---\n"):
    errors.append("no YAML frontmatter at the top of SKILL.md")
else:
    head = md.split("---", 2)[1]
    for field in ("name:", "description:"):
        if field not in head:
            errors.append(f"field {field} missing from frontmatter")
    if "name: tir" not in head:
        errors.append("the name must stay 'tir': anything else imports as a second skill")

# the engine ships next to the skill: it is the source, nothing is transcribed
engine = skill / "scripts" / "cible.py"
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
if "```python" in md:
    errors.append("python block in SKILL.md: the engine belongs in scripts/cible.py")

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
if plugin is not None:
    if plugin.get("name") != root.name:
        errors.append(f"plugin.json name={plugin.get('name')!r} != directory {root.name!r}")
    if not (skill / "SKILL.md").exists():
        errors.append("the skill must live in skills/tir/ to be discovered")

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
print("OK — manifests, frontmatter, shipped engine and commands")
