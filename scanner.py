from pathlib import Path
from datetime import datetime
import sys

SKIP_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
SKIP_SUFFIXES = {".crdownload", ".part", ".partial", ".download", ".tmp"}

SKIP_PATTERNS = (
    ".env", ".pem", ".key", ".p12", ".pfx", ".kdbx", ".ppk",
    "id_rsa", "id_ed25519", "credential", "secret", "password",
    "passport", "aadhaar", "aadhar", "pan_card", "pan card", "driving licence", "driving license",
)

def skip_reason(p: Path):
    """Return why a file is skipped, or None if it should be tidied."""
    name = p.name.lower()
    if name in SKIP_NAMES or name.startswith("."):
        return "hidden or system file"
    if p.suffix.lower() in SKIP_SUFFIXES:
        return "partial download"
    if any(s in name for s in SKIP_PATTERNS):
        return "protected name"
    return None

def scan(folder: str):
    root = Path(folder).expanduser()
    files = []
    for p in sorted(root.iterdir()):         
        if not p.is_file() or p.is_symlink():
            continue
        if skip_reason(p):
            continue
        try:
            st = p.stat()
        except OSError:                        
            continue
        files.append({
            "path": p,
            "name": p.name,
            "ext": p.suffix.lower(),
            "size_kb": round(st.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(st.st_mtime).date().isoformat(),
        })
    return files

if __name__ == "__main__":
    folder = sys.argv[1]
    for f in scan(folder):
        print(f["name"], f["ext"], f["size_kb"], "KB", f["modified"])
    print("\nSkipped (never read or moved):")
    for p in sorted(Path(folder).expanduser().iterdir()):
        if p.is_file() and not p.is_symlink() and skip_reason(p):
            print(" ", p.name, "-", skip_reason(p))