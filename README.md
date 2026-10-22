# File-Tidier

A local file tidier. Point it at a messy folder: it reads each file, gives it a clear name, and sorts it into a folder. The reading is done by a small open model (Gemma 3 through Ollama) on your own laptop. Nothing is uploaded, and it works with Wi-Fi off.

Built for the Hacktoberfest Open-Source AI Challenge, Week 3 ("Slow and Steady").

![Folder before and after](docs/before_after_image.png)

## What it does

- Reads PDFs, Word docs, text files and images.
- Renames messy names from what is inside the file (`bill_final.txt` became `rent_receipt_may_2026.txt`) and leaves good names alone.
- Sorts files into `Study`, `Receipts`, `Travel`, `Photos`, `Work` or `Needs-Review`.
- Shows a preview first and asks before moving anything.
- Undoes the last run, exactly.
- Lazy mode: a watcher tidies each new file a few seconds after it arrives.
- Optional: files not modified for N months go into `Archive/`.

## Demo

![Folder before and after](/Users/hiteshikukreja/Desktop/file-tidier/outputs/output_video.mov)

## Setup

1. Install [Ollama](https://ollama.com) and pull the model:
   ```
   ollama pull gemma3:4b
   ```
2. Install the tool:
   ```
   git clone https://github.com/Kuki-09/file-tidier.git
   cd file-tidier
   python -m venv venv
   source venv/bin/activate
   python -m pip install -r requirements.txt
   ```

Tested on a Mac with Python 3.10.

## Use

```
python cli.py run ~/Downloads/Messy              # preview, then confirm
python cli.py run ~/Downloads/Messy --yes        # skip the confirmation
python cli.py run ~/Downloads/Messy --rename-only            # rename in place, no folders
python cli.py run ~/Downloads/Messy --archive-months 6       # old files go to Archive/
python cli.py undo ~/Downloads/Messy             # reverse the last run

python watcher.py ~/Downloads/Messy              # lazy mode, Ctrl+C to stop
```

The watcher only handles files that arrive after it starts. Tidy what is already there with one `cli.py run`.

## How it works

```
scan -> read a short snippet -> Gemma names and sorts it -> code checks the name
     -> preview -> confirm -> move -> undo log
```

- Only the first 1,500 characters of a document go to the model. Images are shrunk to 896 px first.
- Gemma was good at naming a file from its content and bad at judging whether the old name was fine: it named `some.pdf` correctly, then said to keep `some.pdf`. So a file keeps its old name only when the model and a plain word-overlap check in code both agree.

## Safety

- Nothing leaves your machine. Everything runs through local Ollama.
- Preview first. Nothing moves until you confirm (the watcher has no confirm step, so it never creates folders or touches old files).
- Files are never overwritten. Name clashes get `_2`, `_3`.
- Full undo. Every run writes a log in `.tidy_logs/` inside the folder, with only paths in it.
- Files with sensitive names (`.env`, keys, passwords, passport and similar) are never read or moved.
- It stays in the folder you give it: top level only, no symlinks.

## Results

Tested on a 30-file set I built (PDF, docx, txt, `.pages` and 15 images, including 8 files that already had good names). The answer key was written by hand, after I had seen earlier runs, so treat this as a sanity check and not a benchmark.

|                                   | Result                                                    |
| --------------------------------- | --------------------------------------------------------- |
| Right folder                      | 30 / 30                                                   |
| Right rename-or-keep decision     | 26 / 28                                                   |
| Same folder and name in 3 runs    | 30 / 30                                                   |
| Undo, checked with checksums      | all 30 files byte-identical                               |
| First pass over 30 files          | about 5 min 44 s (about 13 s per image, 7 s per document) |
| Moving the files                  | 0.02 s                                                    |
| Sorting the same 30 files by hand | 10 min 49 s (one person, one try)                         |

## Limits

- It cannot read `.pages` files or scanned PDFs with no text, so those are named from the file name alone.
- A small vision model can misread fine details in images (the year on a rent receipt changed between runs once). That is why undo exists.

## License

MIT
