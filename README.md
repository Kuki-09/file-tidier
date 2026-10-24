# File-Tidier

**A local AI file organizer that understands file contents, gives files meaningful names and sorts them without taking control away from you**

Demo: [Main Demo](https://youtu.be/tXRiyng47rw) · [Watcher Demo](https://youtu.be/ys9RGrQ7zRk) · Evaluation: [eval/EVAL.md](eval/EVAL.md)

File-Tidier uses Gemma 3 4B through Ollama to organize messy folders on your own computer. Instead of relying only on filenames, it reads supported documents and images, proposes descriptive names and sorts files into Study, Personal, Receipts, Travel, Photos, Work, or Needs-Review.

It also supports **optional age-based archiving:** choose an age threshold, such as six months and older files can be moved into Archive/ while preserving their category folders.

A generic bill_final.txt can become Receipts/rent_receipt_may_2026.txt and flight_ticket.pdf, which was really a restaurant bill, became Receipts/restaurant_bill_example.pdf. A misleading filename does not have to dictate where a file goes. If a file cannot be read reliably, it can be routed to Needs-Review rather than treated as something the model understands.

**Preview the plan. Confirm the changes. Undo the run if needed.**

**No cloud AI API. No per-file charges. No server to maintain. And, after setup, no internet connection required.**

Built around the idea of Slow and Steady: automate the small, annoying tasks and get your time back.

![Folder before and after](docs/before_after_image.png)

## Run it

```
ollama pull gemma3:4b
git clone https://github.com/Kuki-09/file-tidier.git && cd file-tidier
python -m venv venv && source venv/bin/activate
python -m pip install -r requirements.txt

python cli.py run ~/Downloads/Messy                          # preview, then confirm
python cli.py run ~/Downloads/Messy --rename-only            # rename in place, no folders
python cli.py run ~/Downloads/Messy --archive-months 6       # old files go to Archive/
python cli.py undo ~/Downloads/Messy                         # reverse the last run
python watcher.py ~/Downloads/Messy                          # lazy mode, Ctrl+C to stop
```

Tested on a Mac with Python 3.10. The watcher handles only files that arrive after it starts. Tidy what is already there with one `cli.py run`.

## How it works

| Step           | What happens                                                                                                            | Code                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| Find files     | Top level only. Skips hidden files, partial downloads, symlinks and sensitive names (`.env`, keys, passwords, passport) | `scanner.py`                    |
| Read           | First 1,500 characters of a PDF, docx or text file. Images are shrunk to 896 px                                         | `extractor.py`, `classifier.py` |
| Name and sort  | Gemma 3 4B through Ollama, JSON checked with pydantic, one retry, then `Needs-Review`                                   | `classifier.py`                 |
| Keep or rename | The old name stays only if the model and a word-overlap check both say it is fine                                       | `planner.py`                    |
| Preview        | Numbered table filling in as each file finishes, then a confirm                                                         | `cli.py`                        |
| Move           | Never overwrites (`_2`, `_3` on a clash). Every folder it creates is logged                                             | `executor.py`                   |
| Undo           | Reverses the latest log and removes only the folders it created                                                         | `executor.py`                   |
| Lazy mode      | Waits until a file stops growing, then tidies only the new files                                                        | `watcher.py`                    |
| Archive        | Optional: files not modified for N months go to `Archive/<folder>`                                                      | `planner.py`                    |

## Safety

- Nothing leaves your machine. Everything runs through local Ollama.
- Preview first. Nothing moves until you confirm. The watcher has no confirm step, so it only touches files that arrive after it starts, and every batch it handles can be undone.
- Files are never overwritten. Name clashes get `_2`, `_3`.
- Full undo. Every run writes a log in `.tidy_logs/` inside the folder, with only paths in it.
- Files with sensitive names (`.env`, keys, passwords, passport and similar) are never read or moved. This checks names only, not what is inside a file.
- It stays in the folder you give it: top level only, no symlinks.

## Why open-source AI?

File-Tidier uses an **open-weight model** locally instead of relying on a closed, hosted AI service for every file.

**Offline use:** After setup and model download, file organization can run without Wi-Fi, provided the local model and required dependencies are available.

**Privacy:** File contents do not need to be uploaded to a third-party AI API.

**No per-file AI costs:** There are no usage-based API charges for classification. Your computer still uses electricity and local processing resources.

**No server to maintain:** Both the organizer and its optional watcher run on your own computer. The watcher does not require a separately hosted server.

**More control:** You can inspect the workflow, experiment with prompts and adapt or replace the model and supporting tools.

**Local AI has trade-offs:** inference can be slower on modest hardware and the model can still make mistakes. The benefit is greater control over your data, infrastructure and usage costs—not a guarantee of perfect results.

## Evaluation and Results

File-Tidier was tested on a 30-file baseline set and on a stress-test set built to break it.

**1.Baseline results**

**Correct destination category:** 30/30 files

**Same folder and filename across three runs:** 30/30 files

**Undo:** all 30 files restored byte-for-byte

These were measured before the Personal folder and the Needs-Review changes, and I have not repeated them on the final version. The answer key was written after earlier runs, so this is a sanity check, not an independent benchmark. **Repeatability also does not prove correctness.**

**2.Stress testing**

The stress set has generic and misleading filenames, a misleading double extension, empty and broken files, blank images, a scanned PDF, unsupported formats, sensitive filenames and a file in a subfolder. All contents are made up.

Run 1 (26 files): 15 as expected, 4 judgment calls and 7 wrong. The 7 wrong: two blank images sorted as photos; three files with nothing readable (an empty .txt, an .xlsx, an .mp3) named and sorted from their file names alone; and two rental agreements sent to Receipts. Misleading names were often fixed from the content: flight_ticket.pdf was a restaurant bill and meeting_minutes.docx was a recipe.

Run 2 (27 files, with a .tar.gz added): after the fix, blank images and files with nothing readable go to Needs-Review with their names unchanged, and the empty notes.txt no longer gets an invented name. Still wrong: receipt.pdf, a rental agreement that says "Not an actual receipt", still goes to Receipts. The Study, Personal and Work boundary is also unreliable, and a reworded category description once moved three ordinary files from Personal to Study.

See [eval/EVAL.md](eval/EVAL.md) for the test setup, results and case-by-case analysis, mistakes and remaining limitations.

**Stress Test Output**

![Folder before and after](docs/Output_2.png)

### Time Comparison

| Task                                    |    Time taken |
| --------------------------------------- | ------------: |
| File-Tidier: first pass over 30 files   | ~5 min 44 sec |
| Manual sorting: one person, one attempt | 10 min 49 sec |

In this trial, File-Tidier completed the first pass faster than sorting the same files manually. Results may vary depending on the files, system and manual sorting approach.

## Limits

- The seven folders are fixed. A file that fits none of them goes to the closest one or to Needs-Review.
- It cannot read `.pages`, `.tar`, or scanned PDFs with no extractable text, so those are named from the file name alone.
- Any blank images or document goes to Needs-Review.
- A small vision model can misread fine details in images (the year on a rent receipt changed between runs once). That is why undo exists.
- Only the top level of a folder is scanned. Files inside subfolders are left alone.
- The watcher is a local convenience feature, not a cloud-hosted service. Your computer must remain running for it to monitor files.

## Data and licences

- Code: MIT (see `LICENSE`).
- Model: Gemma 3 under the Gemma Terms of Use, run locally through Ollama.
- Libraries: typer, rich, ollama, pypdf, python-docx, Pillow, pydantic and watchdog, each under its own licence.
