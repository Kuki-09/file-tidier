"""Times the classifier on every file in a folder and checks it gives the same answer each run.
Reads files only: nothing is moved or renamed.

Usage:  python bench.py <folder> [runs] [model]
        python bench.py ~/Downloads/Dummy_Dataset 3
        python bench.py ~/Downloads/Dummy_Dataset 3 gemma3:12b
Writes bench_results.csv (one row per file per run) and prints a summary.
"""
import csv, sys, time
from collections import defaultdict
from pathlib import Path
import classifier
from classifier import classify
from extractor import extract_text, IMAGE_EXTS
from scanner import scan

folder = sys.argv[1]
runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
if len(sys.argv) > 3:
    classifier.MODEL = sys.argv[3]
files = scan(folder)
if not files:
    sys.exit("No files to test.")

def kind(f):
    if f["ext"] in IMAGE_EXTS:
        return "image"
    return "document" if extract_text(f["path"]) else "no-text"

kinds = {f["name"]: kind(f) for f in files}
print(f"Model: {classifier.MODEL} | {len(files)} files | {runs} runs")
print("Warming up the model (not timed)...")
classify(files[0]["path"])

rows = []
with open("bench_results.csv", "w", newline="") as out:
    w = csv.writer(out)
    w.writerow(["run", "file", "type", "size_kb", "seconds", "category", "new_name", "keep_name", "confidence"])
    for run in range(1, runs + 1):
        for i, f in enumerate(files, 1):
            t = time.perf_counter()
            r = classify(f["path"])
            sec = time.perf_counter() - t
            row = [run, f["name"], kinds[f["name"]], f["size_kb"], round(sec, 1),
                   r.category, r.new_name, r.keep_name, round(r.confidence, 2)]
            rows.append(row)
            w.writerow(row)
            out.flush()                       # keep partial results if you press Ctrl+C
            print(f"[run {run}/{runs}] [{i}/{len(files)}] {f['name']}  {sec:.1f}s")

print("\n=== Seconds per file, by type (all runs) ===")
by_type = defaultdict(list)
for r in rows:
    by_type[r[2]].append(r[4])
for k, v in sorted(by_type.items()):
    print(f"{k:9} {len(v) // runs:3} files   avg {sum(v) / len(v):5.1f}s   max {max(v):5.1f}s")
allsec = [r[4] for r in rows]
print(f"{'all':9} {len(files):3} files   avg {sum(allsec) / len(allsec):5.1f}s   "
      f"total per run {sum(allsec) / runs:.0f}s")

print("\n=== Slowest 3 ===")
for r in sorted(rows, key=lambda r: -r[4])[:3]:
    print(f"{r[4]:5.1f}s  {r[1]} ({r[2]}, {r[3]} KB)")

print("\n=== Consistency across runs ===")
answers = defaultdict(list)
for r in rows:
    answers[r[1]].append((r[5], r[6]))
same_cat = sum(1 for v in answers.values() if len({c for c, _ in v}) == 1)
same_name = sum(1 for v in answers.values() if len(set(v)) == 1)
print(f"Same category every run: {same_cat}/{len(files)}")
print(f"Same category AND name every run: {same_name}/{len(files)}")
for name, v in answers.items():
    if len(set(v)) > 1:
        print(f"  differs: {name}: {sorted(set(n for _, n in v))}")
print("\nSaved bench_results.csv")