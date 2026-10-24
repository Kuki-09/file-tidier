# File-Tidier Evaluation

## Purpose

This evaluation examines whether File-Tidier can organize files based on their contents, preserve useful filenames, handle unreadable or unsupported inputs conservatively, protect sensitive files and avoid processing files outside its intended scope.

File-Tidier uses Gemma 3 4B through Ollama for local classification and filename suggestions. The CLI generates a proposed plan before applying file operations.

The evaluation records both improvements and remaining failures. A descriptive filename is not necessarily accurate and sending a file to `Needs-Review` is useful only when review is warranted.

## 1. Test setup

- **Platform:** macOS
- **Python:** 3.10
- **Model:** Gemma 3 4B through Ollama
- **Stress-test command:**

```bash
python cli.py run ~/Downloads/Test_files --archive-months 6
```

The CLI output is a proposed plan. It does not prove that the operations were applied.

### Test sets

| Test          | Total items in test folder | Files processed | Purpose                                                                                          |
| ------------- | -------------------------: | --------------: | ------------------------------------------------------------------------------------------------ |
| Baseline      |                   30 files |              30 | Initial checks for categories, rename decisions, repeatability and undo                          |
| Stress test 1 |                   28 files |              26 | Test misleading filenames, readable documents, blank or problematic inputs and safety exclusions |
| Stress test 2 |                   29 files |              27 | Examine behavior after refining handling for unreadable or unsupported inputs                    |

The first stress-test folder also contained `.env` and `password.txt`. Both were intentionally excluded from processing. A separate file inside a nested folder was not processed because the scanner operates on top-level files only.

The second stress test added `apache-tomcat-10.1.28.tar.gz` to examine handling of an unsupported archive format. The two runs therefore differed in file count and should not be treated as a perfectly controlled comparison.

## 2. Baseline results

The initial 30-file baseline produced these results:

| Measurement                                | Observed result |
| ------------------------------------------ | --------------: |
| Correct destination folder category        |           30/30 |
| Same folder and filename across three runs |           30/30 |
| Undo restored files byte-for-byte          |           30/30 |

Repeatability measures consistency, not correctness: an incorrect result can also be repeated consistently.

## 3. Prompt Refinement: Filename Generation and Rename Decisions

During testing, I refined the prompt in three stages.

### Stage 1: Rename every processed file

The initial prompt instructed the model to inspect file contents and generate meaningful filenames. The model renamed the files it processed, including files that already had meaningful names. This meant useful filenames could be unnecessarily processed and renamed again.

### Stage 2: Check whether the original filename is meaningful

I then added an instruction asking the model to check whether the original filename was already meaningful. However, the model sometimes judged uninformative filenames, such as `some.pdf` and `ticket_scan_77`, as meaningful. As a result, these filenames were kept even when the model could generate more descriptive names based on the file contents.

This exposed a weakness in the model's judgment: generating a meaningful filename was not the same as correctly deciding whether the original filename should be replaced.

### Stage 3: Let the code have the last word

Gemma was good at writing a name from a file's content and unreliable at judging the old name: for `some.pdf` it wrote `relu_activation_script` and still said to keep `some.pdf`. I tightened the keep rule in the prompt (keep only if the old name clearly says the same thing as the new one, treat generic names such as `untitled`, `scan` and `final` as not good enough, and rename when unsure). I also added a check in code: the old name is kept only if the model says keep and at least 60% of the old name's words appear in the new name.

An earlier attempt to make the model write out a comparison did nothing, because that field was not in its output schema, so I removed it.

After this change, the output on the separate test dataset with filenames such as `some.pdf`, `ticket_scan_7` and `ticket_scan_77` became clean.

**Key lesson:** The challenge was not only generating meaningful filenames, but also making the correct keep-or-rename decision and that decision is better not left to a small model alone.

## 4. Stress-test results

The stress tests included misleading filenames, generic names, readable documents, blank or unreadable inputs, unsupported formats, sensitive filenames and a nested-folder file.

### Run 1: before refining review handling

The test folder contained 28 items. The organizer processed 26 files, leaving `.env` and `password.txt` untouched.

Notable proposed results:

| Input                         | Planned destination                     | Observation                                                                                                                                    |
| ----------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `IMG_001.jpg`                 | `Photos/image_data_001.jpg`             | The image was blank, but it was categorized as a photo and given a descriptive filename instead of being sent to review.                       |
| `broken_document.pdf`         | `Needs-Review/broken_document.pdf`      | The document could not be opened, so routing it to review was appropriate.                                                                     |
| `document.pdf`                | `Needs-Review/empty_pdf_document.pdf`   | The PDF was empty, so routing it to review was appropriate; changing its filename was unnecessary.                                             |
| `ev_charging_invoice.png.pdf` | `Receipts/ev_charging_invoice.pdf`      | Removed a redundant extension while preserving useful identifying words.                                                                       |
| `flight_ticket.pdf`           | `Receipts/restaurant_bill_example.pdf`  | The file contained a restaurant bill and the generated filename reflected its contents despite the misleading original filename.               |
| `meeting_minutes.docx`        | `Personal/cooking_recipe.docx`          | The file contained a cooking recipe and the generated filename reflected its contents despite the misleading original filename.                |
| `monthly_budget.xlsx`         | `Personal/monthly_budget.xlsx`          | The tool cannot read `.xlsx`, so the file was never read. The folder was a guess from the file name that happened to be sensible.              |
| `notes.txt`                   | `Study/study_notes.txt`                 | The file was empty. The model invented a name and a folder from the file name, while the other empty file, `final_v2.txt`, went to review.     |
| `receipt.pdf`                 | `Receipts/rental_agreement_summary.pdf` | The new name fits the content, but the folder is wrong: the file is a rental agreement summary and says "Not an actual receipt".               |
| `recipe.txt`                  | `Personal/employment_checklist.txt`     | The file contained an employment checklist and the name reflects it. I expected `Work`; `Personal` is defensible, so this is a judgment call.  |
| `rental_agreement.pdf`        | `Receipts/rental_agreement.pdf`         | A rental agreement is not proof of a payment, so the folder is wrong. The prompt listed "rent" under Receipts, which probably pulled it there. |
| `scanned_document.pdf`        | `Needs-Review/scanned_document.pdf`     | The PDF is a picture of a page with no text layer. The tool cannot read it, so review with the name unchanged is appropriate.                  |
| `untitled.docx`               | `Needs-Review/untitled_document.docx`   | The document was blank, so routing it to review was appropriate; the descriptive rename was unnecessary.                                       |
| `untitled_image.png`          | `Photos/untitled_image.png`             | The image was blank, but it was categorized as a photo instead of being sent to review.                                                        |
| `podcast_recording.mp3`       | `Study/podcast_recording.mp3`           | Audio cannot be read, but the file was assigned a category from its name instead of being routed to review.                                    |

The test also showed that some files with misleading filenames could be classified using their contents rather than their original names. This is an important capability, but the incorrect or questionable names demonstrate that content-based naming still needs safeguards.

### Run 2: after refining review handling

The test folder contained 29 items, including the additional `apache-tomcat-10.1.28.tar.gz` file. The organizer processed 27 files.

The second run took 94 seconds, approximately 3.5 seconds per processed file according to the CLI output.

| Input                                        | Planned destination                                 | Observation                                                                                                                                                                          |
| -------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `IMG_001.jpg`                                | `Needs-Review/IMG_001.jpg`                          | The image was blank and was correctly routed to review instead of being categorized as a photo.                                                                                      |
| `apache-tomcat-10.1.28.tar.gz`               | `Archive/Needs-Review/apache-tomcat-10.1.28.tar.gz` | Preserved its original name; archive placement and age handling need separate verification.                                                                                          |
| `broken_document.pdf`                        | `Needs-Review/broken_document.pdf`                  | The document could not be opened, so routing it to review was appropriate.                                                                                                           |
| `document.pdf`                               | `Needs-Review/document.pdf`                         | The PDF was empty, so routing it to review was appropriate and its original filename was preserved.                                                                                  |
| `ev_charging_invoice.png.pdf`                | `Receipts/ev_charging_invoice.pdf`                  | Removed the redundant extension while preserving useful identifying words.                                                                                                           |
| `flight_ticket.pdf`                          | `Receipts/restaurant_bill_example.pdf`              | The file contained a restaurant bill, and the generated filename reflected its contents.                                                                                             |
| `grocery_list.txt`                           | `Personal/grocery_list.txt`                         | Placed in `Personal`; the expected category should be checked against the test manifest.                                                                                             |
| `meeting_minutes.docx`                       | `Personal/cooking_recipe.docx`                      | The file contained a cooking recipe, and the generated filename reflected its contents.                                                                                              |
| `monthly_budget.xlsx`                        | `Needs-Review/monthly_budget.xlsx`                  | The file contained budget information and should have been categorized as `Personal`. The `.xlsx` extension had been added after Stress Test 1, so this review result was incorrect. |
| `notes.txt`                                  | `Needs-Review/notes.txt`                            | The notes file was empty, so routing it to review was appropriate.                                                                                                                   |
| `receipt.pdf`                                | `Receipts/rental_agreement_summary.pdf`             | The file contained a rental agreement, so the content-based rename correctly reflected its contents.                                                                                 |
| `recipe.txt`                                 | `Personal/employment_checklist.txt`                 | The file contained an employment checklist and the filename reflected its contents, but the category should have been `Work`.                                                        |
| Scanned PDF (original filename not recorded) | Needs-Review (original filename preserved)          | Scanned-PDF content was unsupported, so the model could not reliably read it; routing it to review was appropriate.                                                                  |
| `untitled.docx`                              | `Needs-Review/untitled.docx`                        | The document was blank, so routing it to review and preserving its original filename were appropriate.                                                                               |
| `untitled_image.png`                         | `Needs-Review/untitled_image.png`                   | The image was blank and was correctly routed to review.                                                                                                                              |
| `podcast_recording.mp3`                      | `Needs-Review/podcast_recording.mp3`                | MP3 content extraction was unsupported, so routing the file to review was appropriate.                                                                                               |

### What changed?

Between Run 1 and Run 2:

- `IMG_001.jpg` and `untitled_image.png` (both blank) moved from `Photos` to `Needs-Review`.
- `notes.txt` (empty) moved from `Study`, with an invented name, to `Needs-Review` with its name kept.
- `podcast_recording.mp3` moved from `Study` to `Needs-Review`.
- `monthly_budget.xlsx` moved from `Personal` to `Needs-Review`. It was a guess in Run 1, and the tool still cannot read it.
- `document.pdf` and `untitled.docx` kept their original filenames.

These changes indicate more conservative handling of several problematic inputs. However, `monthly_budget.xlsx` also being sent to review raises a separate concern: the system may be rejecting some usable files unnecessarily.

The goal is not to maximize the number of files in `Needs-Review`. It is to recognize genuine uncertainty while still organizing files that can be handled reliably.

## 5. Safety and scope observations

### Sensitive files

The `.env` and `password.txt` files were intentionally excluded from processing. This matches the project's intended protection for files with sensitive names.and that decision is better not left to a small model alone.

### Nested folders

The file inside the nested receipt folder was not processed because the scanner is designed to operate on top-level files only. This is expected behavior under the current scope, not a classification failure.

### Undo and preview

The baseline recorded byte-for-byte restoration for all 30 files after undo. The CLI also previews a plan before applying changes.

These safeguards are separate from classification quality. A correct undo does not make a bad rename acceptable and a preview does not guarantee that a proposed name is correct.

## 6. Archiving behavior

Both stress-test runs used `--archive-months 6`. In the second run, the proposed destination for the tar archive was:

`Archive/Needs-Review/apache-tomcat-10.1.28.tar.gz`

This shows that archive placement can interact with review handling. It does not establish that the file's age was correctly calculated or that every archive operation behaves as intended.

Further tests should verify:

- Files older than the threshold are archived.
- Recent files are not archived.
- Review-required files remain identifiable.
- Archive operations can be undone.

## 7. Limitations

- The displayed stress-test results are plans, not proof of applied operations.
- No independent ground-truth manifest was available for every stress-test file.
- Filename and category correctness should be checked against actual file contents.
- The stress-test results do not establish a general accuracy percentage.
- Runtime depends on the machine and local model setup.

## 8. Next experiments

1. Use the same fixed dataset before and after future code changes.
2. Create a ground-truth manifest before testing, including the expected category, acceptable filename, readability and whether review is required.
3. Separate supported readable files from blank, corrupt, ambiguous and unsupported inputs.
4. Measure correct classifications, correct rename-or-keep decisions, invented or misleading names, missed review cases and unnecessary review cases.
5. Test `.env` and password-file exclusion explicitly against the current code.
6. Verify top-level-only scanning and test undo, archive age handling and cancellation.
7. Repeat the same run to evaluate both consistency and correctness.

## Conclusion

The baseline tests showed promising results for category selection, repeatability and undo. The stress tests exposed a more challenging problem: making helpful content-based decisions without inventing details or being unnecessarily conservative.

The second stress test showed improved handling of several problematic inputs, while some misleading filenames and category errors remained. The next milestone is a controlled evaluation with a fixed dataset and an independently prepared answer key.
