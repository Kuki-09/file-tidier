# Evaluation

Every decision, file by file, is in [REVIEW.md](REVIEW.md).

## What was tested

- **Set:** 30 files I put together: 7 PDF, 4 docx, 3 txt, 1 `.pages` and 15 images (receipts, bills, photos, notes). 8 of them were renamed by hand to good names first, as controls the tool should leave alone.
- **Model:** `gemma3:4b` through Ollama, on one Mac, with Wi-Fi on and also off.
- **Answer key:** `eval/answer_key.csv`, written by hand after I had seen earlier runs. Treat the results as a sanity check, not a benchmark.

## How the key was judged

- **Folder:** one correct folder per file. Where a file really fits two (an airline invoice can be Receipts or Travel), both are accepted.
- **Rename:** "rename expected" unless the old name already says specifically what the file is (`flight_invoice_delhi_bengaluru.png` is fine, `speech.txt` is not). Two files are marked "either" and not scored.

## Results

|                               | Result                                                  |
| ----------------------------- | ------------------------------------------------------- |
| Right folder                  | 30 / 30                                                 |
| Right rename-or-keep decision | 26 / 28 (always renaming scores 24 / 28, see below)     |
| `.env` (sensitive name)       | left alone                                              |
| After undo                    | all 30 files byte-identical (`shasum` before and after) |

The two wrong decisions were files with good names that were renamed anyway: `courtyard.jpg` became `courtyard_of_palazzo.jpg`, and `ev_charging_invoice.png` became `charging_invoice_poluppalli.png`. In both, the model voted "rename" even though every word of the old name was in its own new name.

## Keep-or-rename rule, compared

Same 28 scored files and the same model outputs from the first timing pass. Only the rule changes, so this was worked out offline from `bench_results.csv`.

| Rule                                                                       | Right   |
| -------------------------------------------------------------------------- | ------- |
| Never rename                                                               | 9 / 28  |
| Always rename                                                              | 24 / 28 |
| Word check alone (keep if 60% of the old name's words are in the new name) | 24 / 28 |
| Model's vote alone                                                         | 26 / 28 |
| Both must agree (what the tool uses)                                       | 26 / 28 |

What this shows:

- Always renaming already scores 24 / 28. Five of my eight control files have names that match what Gemma writes itself, because I chose them after seeing earlier runs. Only four files really test "leave a good name alone" (`courtyard.jpg`, `ev_charging_invoice.png`, `corgi_dog_in_grass.jpg`, `porsche_on_forest_road.jpg`), and the tool got two of them right.
- The word check alone is the weakest. It keeps `speech.txt`, `attention.pdf`, `rent.png` and `assignment_2.docx`, because one generic word from the old name appears in the new one.
- With the final prompt, the model's vote alone does as well as both together, so the code check changed no result on this set. I kept it as a safety net. With my first prompt, the model said to keep `some.pdf` even though its own name for that file was `relu_activation_script`. That file is not in this set.

## Consistency

3 passes over the same 30 files: the same folder and the same name every time, 30 / 30.

## Speed

- A full run through the CLI took 344 s for 30 files (11.5 s per file). Moving the files took 0.02 s, so almost all of it is the model.
- In the timing script, the first pass took about 304 s. Images were the slow part, about 13 s each, against about 7 s per document.
- The second and third passes took about 176 s and 162 s, with images near 5 s. I do not know why repeat passes are faster. The first pass is the realistic number, because every file the watcher sees is new.
- Sorting the same 30 files by hand took one person 10 min 49 s.

## What this does not show

- One person judged the answers, and only 30 files were used.
- The key was written after seeing earlier runs.
- Only 8 control files test whether good names are left alone.
- One machine and one model size. I did not compare larger Gemma models.

## Reproduce

```
python bench.py <folder> 3                       # timing and consistency, moves nothing
python cli.py run <folder> --yes                 # then, before undo:
python tools/score.py <folder> eval/answer_key.csv
python cli.py undo <folder>
```
