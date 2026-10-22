import time, json, shutil
from pathlib import Path
import typer
from collections import Counter
from rich.console import Console
from planner import build_plan
from scanner import scan
from executor import apply, undo as undo_last

app = typer.Typer(help="Local AI file tidier (Gemma + Ollama)")
console = Console()

def check_folder(folder: str) -> Path:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        console.print(f"[red]Folder not found:[/red] {root}")
        raise typer.Exit(1)
    return root

def fit(text, w):
    return text if len(text) <= w else text[: w - 1] + "…"

class RowPrinter:
    """Prints a bordered table one row at a time. Never redraws, so any length works."""
    def __init__(self, before_w, after_w):
        self.w = [4, before_w, after_w]
        self.count = 0

    def _line(self, l, m, r, f):
        return l + m.join(f * (w + 2) for w in self.w) + r

    def _row(self, cells, v):
        parts = [fit(cells[0], self.w[0]).rjust(self.w[0]),
                 fit(cells[1], self.w[1]).ljust(self.w[1]),
                 fit(cells[2], self.w[2]).ljust(self.w[2])]
        return v + " " + f" {v} ".join(parts) + " " + v

    def header(self):
        typer.echo(self._line("┏", "┳", "┓", "━"))
        typer.echo(self._row(["#", "Before", "After"], "┃"))
        typer.echo(self._line("┡", "╇", "┩", "━"))

    def add(self, before, after):
        if self.count:
            typer.echo(self._line("├", "┼", "┤", "─"))
        self.count += 1
        typer.echo(self._row([str(self.count), before, after], "│"))

    def close(self):
        typer.echo(self._line("└", "┴", "┘", "─"))

@app.command()
def run(folder: str, yes: bool = typer.Option(False, "--yes"),
        rename_only: bool = typer.Option(False, "--rename-only", help="Rename files, don't move them"),
        archive_months: int = typer.Option(0, "--archive-months", min=0,
                                           help="Move files not modified in N months into Archive/")):
    """Preview the plan, ask for OK, then move the files."""
    root = check_folder(folder)
    folder = str(root)
    if rename_only and archive_months:
        console.print("Note: --archive-months is ignored with --rename-only (nothing is moved).")
        archive_months = 0

    start = time.time()
    console.print("Loading model and reading files...")

    names = [f["name"] for f in scan(folder)]
    before_w = max(6, min(max((len(n) for n in names), default=6), 32))
    term = shutil.get_terminal_size((100, 20)).columns
    after_w = max(30, min(term - 10 - 4 - before_w, 70))

    typer.echo("\nPlanned changes (nothing moved yet)")
    table = RowPrinter(before_w, after_w)
    table.header()

    scanned = 0

    def add_row(entry, i, total):
        nonlocal scanned
        scanned = total
        table.add(Path(entry["src"]).name, str(Path(entry["dst"]).relative_to(root)))

    try:
        plan = build_plan(folder, on_file=add_row,
                          rename_only=rename_only, archive_months=archive_months)
    except KeyboardInterrupt:
        typer.echo("\nStopped. Nothing was moved.")
        raise typer.Exit(1)
    except RuntimeError as e:         
        typer.echo("")
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    table.close()

    secs = time.time() - start
    if not plan:
        console.print("Nothing to tidy.")
        raise typer.Exit()

    per_file = secs / scanned if scanned else 0
    console.print(f"Planned {len(plan)} changes from {scanned} files in {secs:.0f}s "
                  f"({per_file:.1f}s per file scanned).")
    failed = sum(1 for m in plan if m.get("confidence") == 0.0)
    if failed:
        console.print(f"{failed} file(s) could not be read and are marked Needs-Review.")

    Path("plan.json").write_text(json.dumps(plan, indent=2))
    if not (yes or typer.confirm("Apply these changes?")):
        console.print("Cancelled. Nothing was moved.")
        raise typer.Exit()

    t0 = time.perf_counter()
    apply("plan.json", folder)
    apply_secs = time.perf_counter() - t0

    moved = sum(1 for m in plan if Path(m["dst"]).exists() and not Path(m["src"]).exists())
    summary = (f"Tidied {moved} of {len(plan)} planned files ({scanned} scanned). "
               f"Planning {secs:.0f}s ({per_file:.1f}s per file), moving {apply_secs:.2f}s.")
    if not rename_only:
        counts = Counter(m["category"] for m in plan)
        summary += " " + ", ".join(f"{k}: {v}" for k, v in counts.items())
        archived = sum(1 for m in plan if m.get("archived"))
        if archived:
            summary += f" (archived: {archived})"
    Path("report.md").write_text(summary + "\n")
    console.print(summary)

@app.command()
def undo(folder: str):
    """Reverse the last run for this folder."""
    undo_last(str(check_folder(folder)))

if __name__ == "__main__":
    app()