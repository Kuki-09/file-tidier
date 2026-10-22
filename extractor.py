from pathlib import Path
from pypdf import PdfReader
from docx import Document

MAX_CHARS = 1500
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(path)
            text = ""
            for page in reader.pages[:3]:
                text += (page.extract_text() or "") + " "
                if len(text) >= MAX_CHARS:
                    break
        elif ext == ".docx":
            text = "\n".join(p.text for p in Document(path).paragraphs)
        elif ext in {".txt", ".md", ".csv"}:
            text = path.read_text(errors="ignore")
        else:
            return ""
    except Exception:
        return ""
    return " ".join(text.split())[:MAX_CHARS]

if __name__ == "__main__":
    import sys
    from scanner import scan
    for f in scan(sys.argv[1]):
        if f["ext"] in IMAGE_EXTS:
            print(f["name"], "-> image (will use vision)")
        else:
            print(f["name"], "->", extract_text(f["path"])[:100] or "(no text found)")