import json, shutil, sys, time
from pathlib import Path

def log_dir(folder):
    return Path(folder).expanduser() / ".tidy_logs"

def remove_if_empty(d):
    """Remove a folder if empty. macOS Finder may have left a .DS_Store in it; ignore that."""
    try:
        junk = d / ".DS_Store"
        if junk.exists() and [p.name for p in d.iterdir()] == [".DS_Store"]:
            junk.unlink()
        d.rmdir()
    except OSError:
        pass

def apply(plan_file, folder):
    plan = json.loads(Path(plan_file).read_text())
    moves, created, failed = [], [], []
    try:
        for m in plan:
            src, dst = Path(m["src"]), Path(m["dst"])
            if not src.exists() or dst.exists():     
                continue
            try:
                if not dst.parent.exists():
                    missing, p = [], dst.parent
                    while not p.exists():          
                        missing.append(p)
                        p = p.parent
                    created.extend(str(x) for x in missing)   
                    dst.parent.mkdir(parents=True)
                shutil.move(str(src), str(dst))
            except OSError:
                failed.append(src.name)               
                continue
            moves.append(m)
    finally:
        if moves:
            d = log_dir(folder)
            d.mkdir(exist_ok=True)
            log = d / f"{time.strftime('%Y-%m-%d_%H%M%S')}.json"
            log.write_text(json.dumps({"moves": moves, "created_dirs": created}, indent=2))
            print(f"Moved {len(moves)} files. Undo log: {log.name}")
        else:
            print("Nothing moved.")
        if failed:
            print(f"Could not move {len(failed)} file(s): {', '.join(failed)}")

def undo(folder):
    d = log_dir(folder)
    logs = sorted(d.glob("*.json")) if d.exists() else []
    if not logs:
        print("Nothing to undo for this folder.")
        return
    latest = logs[-1]
    data = json.loads(latest.read_text())
    restored, blocked = 0, 0
    for m in reversed(data["moves"]):
        src, dst = Path(m["src"]), Path(m["dst"])
        if dst.exists() and not src.exists():
            shutil.move(str(dst), str(src))
            restored += 1
        elif src.exists() and not dst.exists():
            pass                   
        else:
            blocked += 1             
    for c in sorted(data["created_dirs"], key=lambda c: len(Path(c).parts), reverse=True):
        remove_if_empty(Path(c))
    if blocked == 0:
        latest.rename(latest.with_suffix(".undone"))
        print(f"Restored {restored} files from {latest.name}. Done.")
    else:
        print(f"Restored {restored}, blocked {blocked} (original name already taken, or file is gone). Log kept, fix it and run undo again.")

if __name__ == "__main__":
    cmd, folder = sys.argv[1], sys.argv[2]
    if cmd == "undo":
        undo(folder)