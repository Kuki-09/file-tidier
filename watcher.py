import sys, time, json, threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from planner import build_plan
from executor import apply

SETTLE_SECONDS = 10
SKIP_SUFFIXES = {".crdownload", ".part", ".partial", ".download", ".tmp"}

def progress(entry, i, total):
    print(f"  [{i}/{total}] {Path(entry['src']).name} -> "
          f"{Path(entry['dst']).parent.name}/{Path(entry['dst']).name}")

class Handler(FileSystemEventHandler):
    def __init__(self, folder):
        self.folder = Path(folder).expanduser().resolve()
        self.timer = None
        self.pending = set()
        self.lock = threading.Lock()      
        self.run_lock = threading.Lock()   
        self.stopping = False

    def _schedule(self):
        with self.lock:
            if self.stopping:
                return
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(SETTLE_SECONDS, self.tidy)
            self.timer.daemon = True
            self.timer.start()

    def _maybe_schedule(self, path, only_if_pending=False):
        p = Path(path)
        if p.parent != self.folder or p.name.startswith(".") or p.suffix.lower() in SKIP_SUFFIXES:
            return
        with self.lock:
            if only_if_pending and p.name not in self.pending:
                return
            self.pending.add(p.name)
        self._schedule()

    def on_created(self, event):
        if not event.is_directory:
            self._maybe_schedule(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._maybe_schedule(event.dest_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._maybe_schedule(event.src_path, only_if_pending=True)

    @staticmethod
    def _stable(path):
        try:
            size = path.stat().st_size
            time.sleep(1)
            return size == path.stat().st_size
        except OSError:
            return True       

    def tidy(self):
        with self.run_lock:
            with self.lock:
                batch = set(self.pending)
                self.pending.clear()
            if not batch:
                return
            unstable = {n for n in batch if not self._stable(self.folder / n)}
            if unstable:                     
                with self.lock:
                    self.pending |= unstable
                batch -= unstable
                self._schedule()
            if not batch:
                return
            start = time.time()
            print("New files detected, tidying...")
            try:
                plan = build_plan(str(self.folder), on_file=progress, only=batch)
                if plan:
                    Path("plan.json").write_text(json.dumps(plan, indent=2))
                    apply("plan.json", str(self.folder))
                else:
                    print("Nothing to move.")
                print(f"Done in {time.time() - start:.0f}s.")
            except Exception as e:           
                print(f"Could not tidy these files: {e}")
                print("Run `python cli.py run <folder>` once Ollama is ready.")
            print("Watching for new files...")

    def shutdown(self):
        with self.lock:
            self.stopping = True
            if self.timer:
                self.timer.cancel()
            left = len(self.pending)
        with self.run_lock:                  
            pass
        return left

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python watcher.py <folder>")
    folder = Path(sys.argv[1]).expanduser().resolve()
    if not folder.is_dir():
        sys.exit(f"Folder not found: {folder}")
    handler = Handler(folder)
    observer = Observer()
    observer.schedule(handler, str(handler.folder), recursive=False)
    observer.start()
    print(f"Watching {handler.folder}. Drop a file in. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        observer.stop()
        left = handler.shutdown()
        if left:
            print(f"{left} new file(s) were not tidied. Run `python cli.py run <folder>` to sort them.")
    observer.join()