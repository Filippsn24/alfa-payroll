"""One-off: extract group->project pairs from tatyana-payroll.gs into JSON."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / ".cursor" / "projects" / "empty-window" / "tatyana-payroll.gs"
if not GS.exists():
    GS = Path(r"C:\Users\Филипп\.cursor\projects\empty-window\tatyana-payroll.gs")

text = GS.read_text(encoding="utf-8")
m = re.search(r"function getGroupProjectPairs_\(\) \{\s*return \[([\s\S]*?)\];\s*\}", text)
if not m:
    raise SystemExit("pairs not found")
pairs = re.findall(r"\['([^']*)',\s*'([^']*)'\]", m.group(1))
out = ROOT / "data" / "group_project_pairs.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {len(pairs)} pairs to {out}")
