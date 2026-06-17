# CIMAC Harmonization — Project Handoff (Current State)

Durable handoff. Last refreshed at the end of the **2026-06-09** session
(below). Prior refresh: **2026-05-26** (CIDC follow-up workbook + Phase 2 QC).

---

## 0. Latest changes (2026-06-09) — screen-failure exclusions + 10026 relabel

Edgar confirmed our harmonization **replaces** his prior 9-trial harmonization,
so the main 9-trial output no longer has to reproduce his old template exactly.
The output model is now **two roles, three files**:

| File | Role | Rows | Screen failures | 10026 treatment |
|---|---|---:|---|---|
| `harmonized_9trials_reproduced.csv` | **Historical / template-reproduction QC** | 1,781 | retained (ghosts) | `ipi_dec` (normalized ≡ `ipi_aza` at validation) |
| `harmonized_9trials_gold.csv` *(new)* | **Current gold 9-trial** | 1,771 | excluded | `ipi_dec` |
| `harmonized_11trials.csv` | **Current gold deliverable** | 1,990 | excluded | `ipi_dec` |

**Screen-failure exclusions (clinical team, 2026-06).** 7 × 10026
(CBUP3C3, CBUPHYS, CBUPJ05, CBUPJUT, CBUPP1Y, CBUPQS0, CBUPWJU) + 3 × ABTC1603
(CG076LL, CG078BY, CG07TB8) were screen failures with no clinical data — they
existed only as anchor-only ghost rows in Edgar's template. Declared in
`harmonization_config.yaml` under a new top-level `excluded_participants:` block
and applied **once** in `extract_harmonized_clinical.py`. **Excluded** from the
two gold outputs; **retained** in the QC reproduction + `provenance_long.csv`;
documented in generated `harmonization_outputs/excluded_participants.csv`.
Their 115 resolved low-confidence flags were dropped from
`flagged_for_review.csv`, and the CIDC workbook's 10026/ABTC1603 missing-data
sheets are now empty (they were exactly these patients).

**10026 treatment relabel `ipi_aza` → `ipi_dec`** (ipilimumab + decitabine).
Source-backed: `treatment_dose_04282024.csv` = 1,236 Decitabine + 149
Ipilimumab; zero azacitidine in study-treatment files (azacitidine/Vidaza is
prior therapy only). One-line config change (`10026.trial_constants.treatment`).
`validate_extractions.py` adds a scoped in-memory normalization
(`TEMPLATE_VALUE_NORMALIZATIONS`: template 10026 `ipi_aza` ≡ pipeline `ipi_dec`)
so the approved relabel produces **no artificial mismatches** — validation
holds steady at **770**.

**Post-run state:** `exclusion_and_order_checks.txt` → **VERDICT: PASS** (new
checks [11]/[12] cover gold outputs + the relabel); 11-trial = 1,990; gold
9-trial = 1,771; QC reproduction = 1,781 (row order still matches template);
provenance = 37,988; flagged = 3,856; 0 BACCI; row-order diagnostics clean.

**Note for next session:** §1, §3–§5 below still describe the pre-2026-06-09
state (2,000 rows, single 9-trial output, `ipi_aza`). This section supersedes
those numbers; update them on the next material change.

---

## 0a. 10013 OS/PFS resolved-explained + mIF sample-ID follow-up (2026-06-09)

Read-only investigation (no pipeline/code/output changes). Two updates to
10013 status:

**10013 OS/PFS missingness is now RESOLVED / EXPLAINED — not an extraction
problem.** Per clinical-expert feedback: 10013 was a **neoadjuvant** trial with
**pCR and TIL percentage** as primary endpoints. **OS and PFS were not
provided** in the clinical data, and prior trial-team feedback indicated there
were **insufficient OS/PFS data for informative analysis**. Confirmed in the
output: all 196 10013 rows have `os_time`/`os_stat`/`pfs_time`/`pfs_stat`
empty. These should **remain missing** and should **no longer be flagged as
unresolved** — leave them missing unless a newer source dataset is provided.
(This reframes the 10013 line in §3.3 / §6 item 4 from "unresolved missing
clinical data" to "endpoints explained; sample IDs pending CIDC.")

**Remaining 10013 follow-up is sample-ID related (Cimac.id).** A read-only
search found **no mIF specimen manifest and no mIF assay metadata** with
sample-level CIMAC IDs anywhere in the repository. The only 10013 imaging
present is H&E whole-slide `.svs` files at `/vf/.../CIMAC/10013/hande/`
(`CHCO*.01`, 34 slides, one `.01` per participant, no collection-event label,
covering only 34/51 participants) — H&E, not mIF, and not an official manifest.
`10013-clinical/specimen_collection_*.csv` carries collection events (Baseline,
Post Cycle 1, Definitive Surgery, Post Cycle 3) but only 7-char participant IDs,
no sample-level Cimac.id. Therefore the **196 10013 `Cimac.id` values cannot be
filled reliably from current repository contents.**

**Needed from CIDC/CSMS:** (1) the **official mIF specimen manifest** mapping
`cimac_part_id + collection event → Cimac.id`; and (2) confirmation of the
**Post Cycle 3 → mIF-manifest event** mapping (already confirmed: Baseline →
Baseline, Definitive Surgery → Surgical Resection, Post Cycle 1 → Day 18 to 22).

---

## 1. Current project state

- **Repository.** CIMAC clinical harmonization pipeline. Reproducible
  Python pipeline that harmonizes per-sample clinical data across CIMAC
  cancer trials into a single 19-column table keyed on
  `(trial, cimac_part_id, Cimac.id, Collection_Event)`. Reproduces the
  9-trial reference (`cross_trial_analysis_egk_april30_meta_9trials.csv`)
  from raw source files and extends it to two new trials (10013, 14C0059G).
- **Current scope. 11 trials. BACCI is intentionally excluded** (not part
  of the CIMAC trial set; source directory removed; not registered in the
  orchestrator or YAML; the legacy `scripts/extractors/bacci.py` is kept on
  disk for history only and is not imported).
- **Main output.** `harmonization_outputs/harmonized_11trials.csv` — the
  primary deliverable (2,000 rows × 19 columns, 11 trials).
- **9-trial reproduced output.** `harmonization_outputs/harmonized_9trials_reproduced.csv`
  — row-aligned to the 9-trial reference for direct comparison (1,781 rows × 19 columns).
- **Phase 2 QC (2026-05-26).** Confirmed the 11-trial output is consistent
  with the 9-trial reproduced output for overlapping trials:
  - 1,781 overlapping rows (all 9 trials)
  - 26,715 compared value cells (1,781 rows × 15 value fields)
  - **0 value differences**
  - Row ordering differs as expected (9-trial file is sorted to match
    the reference; 11-trial file uses its own ordering)
- **One-command run script.** `./scripts/run_full_harmonization.sh` runs the
  full 9-step pipeline (`set -euo pipefail`; stops on first failure).
- **Environment.**
  ```bash
  cd /gpfs/gsfs12/users/nextgen2/james/data/CIMAC/harmonization
  source .venv/bin/activate              # Python 3.10
  ./scripts/run_full_harmonization.sh
  ```

---

## 2. Reviewer-decision implementation (completed 2026-05-20)

The following changes were implemented with the full pipeline re-run after
each phase. All changes are reproducible from
`scripts/config/harmonization_config.yaml` and the per-trial extractors —
no manual edits to harmonized CSVs.

### 2.1 Global schema rename

- **`BOR` → `clinical_benefit`** (primary harmonized output column).
- **`BOR.binary` → `clinical_benefit.binary`** (binary response-bucket).
- **No `BOR` / `BOR.binary` alias columns retained** in the final
  harmonized outputs (`harmonized_11trials.csv`,
  `harmonized_9trials_reproduced.csv`, `provenance_long.csv`).
- **Validation comparison** uses an in-memory schema-mapping layer.
  `scripts/validate_extractions.py` defines
  `TEMPLATE_TO_PIPELINE = {"BOR": "clinical_benefit", "BOR.binary": "clinical_benefit.binary"}`
  and renames the reference columns at read time. The reference file on
  disk is unchanged.
- **Provenance lineage strings retained.** Where positional `source_file`
  or `source_column` arguments to provenance cells originally read `BOR` /
  `BOR.binary` (e.g., `"DERIVED:BOR"`, `source_column="BOR"`), they were
  intentionally **kept** — these describe derivation lineage, not output
  schema. The output `harmonized_field` of every provenance row uses the
  renamed `clinical_benefit` / `clinical_benefit.binary` names.

### 2.2 Item-level reviewer decisions implemented

- **10104 `clinical_benefit` / `clinical_benefit.binary` source-backed.**
  Pipeline emits source values verbatim; reference values do NOT
  override source files.
- **E4412 Unevaluable → lowercase `other`.** A `contains: "Unevaluable"`
  rule in `value_normalizations.clinical_benefit` collapses all bracketed
  variants to lowercase `other` for both `clinical_benefit` and
  `clinical_benefit.binary`. E4412 clinical_benefit and
  clinical_benefit.binary match rates are now 1.000 (167/167 each).
- **S1400I `age` uses source integer `age_num`.** Per reviewer decision,
  the integer enrollment age from `Clinical Dataset 2023_03_14.csv` is
  substituted. Implementation: confidence 0.95,
  `extraction_method = age_at_enrollment_integer_substitute`. All 561
  S1400I rows now have a populated `age`. 511 rows remain mismatched
  against the reference (integer vs decimal divergence — reviewer-approved).
- **9204 race `Other` → `Other`.** Source value `Other` preserved verbatim.
  Reviewer-approved divergence from reference (reference has `unk`).
- **9204 `Collection_Event_alt` `Day_8` → `first_sample_post_treatment`.**
  Reviewer-approved divergence from reference (reference has `C2`).

### 2.3 Confirmed without code changes (left in place)

- **`pfs_bin` 120-day landmark rule.** All 2,000 rows carry
  `extraction_method = derived_pfs_bin_120d`.
- **`bor_bin` 120-day SD-landmark rule.** All 2,000 rows carry
  `extraction_method = derived_bor_bin_120d`.
- **10026 CRm / CRi → `R` mapping.** `CRm`, `CRi`, `CR with MRD-`,
  `CR with incomplete count recovery` all map to `R` in
  `clinical_benefit.binary`. 36 rows affected.
- **E4412 time conversion `round(months × 30.4375)`.** Remains `round()`,
  not `int()`. 19 off-by-1-day mismatches remain.

---

## 3. CIDC-facing clinical follow-up workbook (completed 2026-05-26)

### 3.1 Overview

Created a CIDC-facing Excel workbook for clinical team follow-up:

```
harmonization_outputs/cidc_clinical_followup.xlsx
```

Generated by standalone script:

```
scripts/build_review_workbook.py
```

The workbook is framed for CIDC / clinical team consumption and **avoids
internal terminology** including: Edgar, template, reproduced, mismatch,
9-trial, 11-trial, both_missing. The script uses internal files
(validation_report.csv, provenance_long.csv) to identify rows, but the
workbook itself uses neutral clinical follow-up language.

### 3.2 Workbook sheets (11 total)

| # | Sheet name | Rows | Purpose |
|---|-----------|-----:|---------|
| 1 | `README_Index` | 10 | Workbook index |
| 2 | `ABTC1603_pfs_stat` | 18 | Endpoint-rule follow-up: should death without progression count as PFS event? |
| 3 | `Missing_values_summary` | 229 | One row per affected sample across 4 trials |
| 4 | `10026_missing_values_long` | 112 | Long format: 7 samples × 16 fields |
| 5 | `ABTC1603_missing_values_long` | 48 | Long format: 3 samples × 16 fields |
| 6 | `10013_missing_values_long` | 3,136 | Long format: 196 samples × 16 fields |
| 7 | `14C0059G_missing_values_long` | 368 | Long format: 23 samples × 16 fields |
| 8 | `10026_source_rows_found` | 1 | No-match summary |
| 9 | `ABTC1603_source_rows_found` | 1 | No-match summary |
| 10 | `10013_source_rows_found` | 993 | Raw source rows found |
| 11 | `14C0059G_source_rows_found` | 136 | Raw source rows found |

### 3.3 Missing-values summary by trial

| Trial | Samples | Missing cells | % missing | Key gaps | Raw source rows found |
|-------|--------:|--------------:|----------:|----------|----------------------|
| 10026 | 7 | 91/112 | 81% | All fields except treatment missing; PIDs not in source files | 0 (in 4 CSVs) |
| ABTC1603 | 3 | 36/48 | 75% | All fields except treatment + clinical_benefit.binary missing; PIDs not in source files | 0 (in 4 CSVs) |
| 10013 | 196 | 2,156/3,136 | 69% | Cimac.id 100% missing; survival/arm/phase/CE_alt 100% missing; demographics + clinical_benefit present | 993 (in 5 CSVs) |
| 14C0059G | 23 | 161/368 | 44% | Cimac.id 100% missing; age/arm/phase/CE_alt 100% missing; partial survival data present | 136 (in 7 CSVs) |

### 3.4 Display and column conventions

- Missing `Cimac.id` displays as `"missing"` in the workbook only;
  underlying harmonized CSVs are unchanged.
- The summary column formerly named `source_files_or_provenance_missing`
  was renamed to `source_record_status` for CIDC clarity. Cell values
  now use phrases like "no matching source rows found", "matching source
  records found", "source records found, but selected harmonized fields
  still missing in source".
- `ABTC1603_pfs_stat` internal labels were renamed to CIDC-friendly
  labels: `clinical_team_reference_field/value`,
  `current_harmonized_field/value`, `difference_type`,
  `current_value_missing`.
- 12 long-format rows lack provenance (expected for derived fields on
  missing samples: ABTC1603 os_time/os_stat/pfs_time/pfs_stat for 3
  patients).

---

## 4. Latest validation results

Pipeline ran end-to-end after every change. Final state:

- `./scripts/run_full_harmonization.sh` completed all 9 steps cleanly.
- `harmonization_outputs/exclusion_and_order_checks.txt` ends with
  **`VERDICT: PASS — all checks satisfied.`**
- **`harmonized_11trials.csv`: 2,000 rows × 19 columns**, 11 trials.
- **`harmonized_9trials_reproduced.csv`: 1,781 rows × 19 columns**,
  row-aligned to reference (`row_order_diagnostics.csv` contains
  only the `summary` row).
- **BACCI rows in any output: 0**.
- **`validation_report.csv` mismatches: 770** (down from baseline 836
  before the 2026-05-20 implementation pass).
- **`flagged_for_review.csv` rows: 3,971** (down from baseline 4,542).
- **Schema rename integrity.** `harmonized_11trials.csv` has
  `clinical_benefit` and `clinical_benefit.binary` columns; **no `BOR`
  or `BOR.binary` columns**.

---

## 5. Current important output paths

All under `harmonization_outputs/`:

| File | Purpose |
|---|---|
| `harmonized_11trials.csv` | Primary deliverable (2,000 × 19). |
| `harmonized_9trials_reproduced.csv` | Reference-aligned 9-trial fidelity check (1,781 × 19). |
| `cidc_clinical_followup.xlsx` | CIDC-facing clinical follow-up workbook (11 sheets). |
| `provenance_long.csv` | Per-cell audit trail (37,988 rows). |
| `flagged_for_review.csv` | Below-threshold cells → NA + flag (3,971 rows). |
| `validation_summary.csv` | Per-(trial, column) match rate vs reference. |
| `validation_report.csv` | One row per mismatching cell (770 rows). |
| `row_order_diagnostics.csv` | Reference row-order audit (healthy: only `summary` row). |
| `exclusion_and_order_checks.txt` | One-shot PASS/FAIL audit; look for `VERDICT: PASS`. |
| `final_handoff_report.md` | Auto-generated narrative + per-trial breakdown. |
| `top_review_items_with_source_evidence.md` | Decision queue with source-file citations. |
| `gu16257_pfs_time_fallback_investigation.md` | GU16-257 `pfs_time` fallback investigation. |

Scripts:

| File | Purpose |
|---|---|
| `scripts/run_full_harmonization.sh` | One-command 9-step pipeline runner. |
| `scripts/build_review_workbook.py` | Standalone CIDC follow-up workbook generator. |

---

## 6. Email context — CIDC / clinical team follow-up

James planned to send an email to a clinical team contact explaining that
the workbook (`cidc_clinical_followup.xlsx`) is intended for CIDC / clinical
team and asks for help with five follow-up categories:

1. **ABTC1603 pfs_stat:** Confirm whether death without documented
   progression should count as a PFS event (15 pfs_stat + 3 downstream
   pfs_bin cells affected).

2. **10026 missing clinical data:** 7 affected patient/sample rows have
   broad missing clinical data (92.9% of fields missing) and no matching
   raw source rows were found in any source file.

3. **ABTC1603 missing clinical data:** 3 affected patient/sample rows have
   broad missing clinical data (85.7% of fields missing) and no matching
   raw source rows were found in any source file.

4. **10013 missing sample identifiers and clinical fields:** Source rows
   were found (993 rows across 5 files), but Cimac.id is missing for all
   196 rows and several clinical fields (survival, arm, phase,
   Collection_Event_alt, clinical_benefit.binary) remain unavailable.

5. **14C0059G missing sample identifiers and clinical fields:** Source rows
   were found (136 rows across 7 files), but Cimac.id is missing for all
   23 rows and remaining age/arm/phase/collection-event gaps exist.

---

## 7. Known deferred items / cautions

- **`template_anomalies.csv` was NOT updated.** Adding entries for
  reviewer-approved pipeline-vs-reference divergences was intentionally
  deferred. Decide separately whether to add these as documented anomalies.
- **Slide decks were NOT updated.** `five_examples_9trial_harmonization_check.docx`
  and `expanded_reviewer_examples_draft.md` still reference `BOR` /
  `BOR.binary` in narrative content.
- **`README.txt` was NOT updated.** It still references `BOR` / `BOR.binary`
  in its narrative.
- **GU16-257 `pfs_time` fallback was NOT changed.** No final reviewer
  decision was provided. The fallback rule remains "first non-null of
  `[DFSTIM, DRFSTIM]`" with 4 residual mismatches; the candidate
  refinement (require `RECCUR` non-null before accepting `DFSTIM`) is
  documented in `gu16257_pfs_time_fallback_investigation.md`.
- **`bacci.py` was left untouched.** BACCI is excluded and the extractor
  is historical.
- **Provenance lineage strings may still reference `BOR`.** This is by
  design — they document derivation lineage, not output schema.
- **"Pending final clinical confirmation" wording** remains in
  `provenance_long.csv` `notes` for `bor_bin` and `pfs_bin` cells.
- **E4412 time rounding** remains `round()` (19 off-by-1-day mismatches).

---

## 8. Files likely relevant next time

### Handoff and context
- `PROJECT_HANDOFF_CURRENT_STATE.md` (this file)
- `cimac_clinical_team_review.pptx`
- `cimac_to_do.pptx`
- `cross_trial_analysis_egk_april30_meta_9trials.csv`

### CIDC follow-up workbook
- `harmonization_outputs/cidc_clinical_followup.xlsx`
- `scripts/build_review_workbook.py`

### Core harmonized outputs
- `harmonization_outputs/harmonized_11trials.csv`
- `harmonization_outputs/harmonized_9trials_reproduced.csv`
- `harmonization_outputs/provenance_long.csv`
- `harmonization_outputs/flagged_for_review.csv`

### Validation
- `harmonization_outputs/validation_summary.csv`
- `harmonization_outputs/validation_report.csv`
- `harmonization_outputs/exclusion_and_order_checks.txt`
- `harmonization_outputs/row_order_diagnostics.csv`

### Reports
- `harmonization_outputs/final_handoff_report.md`
- `harmonization_outputs/top_review_items_with_source_evidence.md`

### Source directories for follow-up trials
- `10026-clinical/`
- `ABTC1603-clinical/`
- `10013-clinical/`
- `14C0059G-clinical/`

---

## 9. Suggested next steps

1. **Wait for CIDC / clinical team feedback** on
   `cidc_clinical_followup.xlsx`. The email with the workbook is the
   next action.
2. **If CIDC provides additional source data,** add it to the appropriate
   trial source directories, update `harmonization_config.yaml` and/or
   the per-trial extractor as needed, rerun
   `./scripts/run_full_harmonization.sh`, and regenerate the workbook
   with `python scripts/build_review_workbook.py`.
3. **Decide whether to document reviewer-approved divergences** in
   `template_anomalies.csv` (10104 source-backed ~26 cells; 9204 race
   `Other` × 2; 9204 `Day_8` × 2; CD5Z7O5 age 64; S1400I 511
   decimal-vs-integer age cells; 10026 CRm/CRi → R 54 cells).
4. **Decide whether to update slide decks and static README docs** to use
   `clinical_benefit` / `clinical_benefit.binary` terminology.
5. **Decide whether GU16-257 `pfs_time` fallback needs a final reviewer
   decision** (require `RECCUR` non-null before accepting `DFSTIM`).
   4 residual `pfs_time` mismatches + 2 downstream `pfs_bin` mismatches.
6. **Decide whether to drop the "pending final clinical confirmation"
   wording** from `provenance_long.csv` `notes` for `bor_bin` / `pfs_bin`.
7. **Continue avoiding manual edits to harmonized CSVs.**

---

## 10. Safety / reproducibility rules

- **Never manually edit any harmonized CSV in `harmonization_outputs/`.**
  Manual edits break provenance, fail the next validation pass, and get
  silently overwritten by the next pipeline run.
- **Make changes through config or code only.** Preferred location:
  `scripts/config/harmonization_config.yaml`. Only touch the per-trial
  extractor in `scripts/extractors/` when new logic is required.
- **Always rerun `./scripts/run_full_harmonization.sh` end-to-end** after
  any config / code change.
- **Always check `exclusion_and_order_checks.txt`** for `VERDICT: PASS`.
- **Confirm `harmonized_11trials.csv` is 2,000 rows × 19 cols, contains
  exactly 11 trials, and has zero BACCI** before sharing or analyzing.
- **Preserve provenance.** Every cell in the harmonized output must trace
  back to `(source_file, source_column, source_row_idx, extraction_method)`
  in `provenance_long.csv`.
- **Avoid loose scratch files under shared `/tmp` on Biowulf.** Use a
  project-local scratch directory such as `./tmp/`, `./scratch/`,
  `harmonization_outputs/_scratch/`, or `${TMPDIR}` /
  `/lscratch/${SLURM_JOB_ID}` if available. Clean up when done.
- **Ask before making schema-changing or reviewer-facing changes.**

---

## Where to start next time — 7-step checklist

1. `cd /gpfs/gsfs12/users/nextgen2/james/data/CIMAC/harmonization`,
   `source .venv/bin/activate`.
2. `tail -5 harmonization_outputs/exclusion_and_order_checks.txt` —
   confirm `VERDICT: PASS`.
3. Read § 1–§ 5 above to refresh scope, decisions, output paths, and
   the latest validation numbers.
4. Read § 6–§ 7 above for CIDC follow-up status and what's still open.
5. If CIDC feedback has arrived, route changes through
   `scripts/config/harmonization_config.yaml` first, then per-trial
   extractor only when new logic is required. Preserve provenance.
6. Rerun `./scripts/run_full_harmonization.sh` after any change; re-audit
   against the numbers in § 4 and verify only intended deltas moved.
7. Update this handoff doc when material changes land.
