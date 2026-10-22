"""Scores a tidy run against answer_key.csv.

Usage (run BEFORE undoing):
  python score.py ~/Downloads/Dummy_Dataset ~/Desktop/answer_key.csv

Reads the newest log in <folder>/.tidy_logs (normal mode: category = destination
folder; Archive/<category> counts as <category>). In the key, expected_category
may list several acceptable answers separated by | (for example Study|Needs-Review).
rename_expected is yes, no, or either (either = not scored).
"""
import csv, json, re, sys
from pathlib import Path

def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def name_changed(src_stem, dst_stem):
    a, b = norm(src_stem), norm(dst_stem)
    return not (a == b or re.fullmatch(re.escape(a) + r"_\d+", b))   # _2 = collision suffix, not a rename

folder = Path(sys.argv[1]).expanduser()
key = Path(sys.argv[2]).expanduser()

logs = sorted((folder / ".tidy_logs").glob("*.json"))
if not logs:
    sys.exit("No .tidy_logs/*.json found. Run the tidier first (and don't undo yet).")
moves = {Path(m["src"]).name: Path(m["dst"]) for m in json.loads(logs[-1].read_text())["moves"]}

rows = list(csv.DictReader(open(key)))
cat_ok = cat_n = ren_ok = ren_n = 0
for r in rows:
    name, exp, ren = r["filename"], r["expected_category"], r["rename_expected"]
    accepted = exp.split("|")
    if exp == "SKIPPED":
        status = "OK" if name not in moves else "MOVED (should be skipped!)"
        print(f"[skip] {name}: {status}")
        continue
    cat_n += 1
    if name not in moves:
        print(f"[miss] {name}: not moved")
        continue
    dst = moves[name]
    got = dst.parent.name                       # Archive/Study/x.pdf -> Study
    if got in accepted:
        cat_ok += 1
    else:
        print(f"[cat ]  {name}: expected {exp}, got {got}")
    if ren == "either":                         # both outcomes are acceptable
        continue
    changed = name_changed(Path(name).stem, dst.stem)
    ren_n += 1
    if changed == (ren == "yes"):
        ren_ok += 1
    else:
        print(f"[name]  {name}: rename expected={ren}, got {dst.name}")

print(f"\nCategory accuracy: {cat_ok}/{cat_n} = {100 * cat_ok / max(cat_n, 1):.0f}%")
print(f"Rename decision accuracy: {ren_ok}/{ren_n} = {100 * ren_ok / max(ren_n, 1):.0f}%")