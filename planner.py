import re, json, sys, time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from scanner import scan
from classifier import classify

def clean(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60] or "file"

def name_words(s):
    return {w for w in re.split(r"[^a-z]+", s.lower()) if len(w) > 2}

def already_good(orig_stem, new_name):
    o, n = name_words(orig_stem), name_words(new_name)
    return bool(o) and len(o & n) / len(o) >= 0.6

def is_old(path, months):
    return months > 0 and (time.time() - path.stat().st_mtime) > months * 30.44 * 86400

def build_plan(folder: str, on_file=None, rename_only=False, only=None, archive_months=0):
    root = Path(folder).expanduser()
    files = scan(folder)
    if only is not None:
        files = [f for f in files if f["name"] in only]
    plan, used = [], set()
    for i, f in enumerate(files, 1):
        r = classify(f["path"])
        cat = r.category if r.confidence >= 0.5 else "Needs-Review"
        stem = Path(f["name"]).stem
        base = stem if (r.keep_name and already_good(stem, r.new_name)) else clean(r.new_name)
        archived = (not rename_only) and is_old(f["path"], archive_months)
        if rename_only:
            dest_dir = root
        elif archived:
            dest_dir = root / "Archive" / cat
        else:
            dest_dir = root / cat
        target = dest_dir / f"{base}{f['ext']}"
        if target == f["path"]:    
            continue
        n = 2
        while target.exists() or target in used:
            target = dest_dir / f"{base}_{n}{f['ext']}"
            n += 1
        used.add(target)
        entry = {"src": str(f["path"]), "dst": str(target), "category": cat, "archived": archived}
        plan.append(entry)
        if on_file:
            on_file(entry, i, len(files))
    return plan

def show(plan, root):
    t = Table(title="Planned changes (nothing moved yet)")
    t.add_column("Before"); t.add_column("After")
    for m in plan:
        t.add_row(Path(m["src"]).name, str(Path(m["dst"]).relative_to(root)))
    Console().print(t)

if __name__ == "__main__":
    folder = sys.argv[1]
    plan = build_plan(folder)
    show(plan, Path(folder).expanduser())
    Path("plan.json").write_text(json.dumps(plan, indent=2))