# Plan: 9-Trial Clinical Team Review Excel Workbook (Current Follow-Up Items Only)

Generated 2026-05-26 from:
- `cimac_clinical_team_review.pptx` (3 slides; 3 populated 9-trial example types)
- `harmonization_outputs/validation_report.csv` (770 total mismatches; 28 in scope)
- `harmonization_outputs/provenance_long.csv`
- `harmonization_outputs/harmonized_9trials_reproduced.csv`
- `cross_trial_analysis_egk_april30_meta_9trials.csv`

No code, config, harmonized CSVs, or existing reports are modified by this plan.

---

## 1. Executive summary

This is a **narrow workbook for current clinical-team follow-up items only.**

It is **not** a comprehensive 9-trial discrepancy workbook. All other known
9-trial discrepancies (120-day landmark rules, CRm/CRi, 10104 anchor,
e4412 rounding, s1400i age, gu16257 pfs_time, 9204 small diffs, etc.) are
either already settled with the reviewers or are being worked out separately.
They are explicitly excluded from this workbook.

**Scope:** Only the 3 example types explicitly shown as current 9-trial
follow-up items in `cimac_clinical_team_review.pptx`:

| # | Trial | Field(s) | Cells | Slide |
|---|-------|----------|------:|-------|
| 1 | ABTC1603 | pfs_stat + downstream pfs_bin | 18 | Slide 1 — "Possible rule refinements" |
| 2 | 10026 | treatment | 7 | Slide 2 — "Template anomalies vs source-backed values" |
| 3 | ABTC1603 | treatment | 3 | Slide 2 — "Template anomalies vs source-backed values" |

**Total cells in workbook:** 28.

---

## 2. Included worksheets

### Output file

```
harmonization_outputs/clinical_team_review_9trial_current_followup.xlsx
```

### Worksheets (4 total)

| # | Sheet name | Example type | Trial | Field(s) | Rows | Status |
|---|-----------|-------------|-------|----------|-----:|--------|
| 0 | `README_Index` | Index / legend | — | — | 3 | — |
| 1 | `ABTC1603_pfs_stat` | Death-without-progression not counted as PFS event | ABTC1603 | pfs_stat, pfs_bin | 18 | Unresolved; follow-up with clinical team / CIDC |
| 2 | `10026_treatment` | Trial-constant `ipi_aza` vs Edgar/template blanks | 10026 | treatment | 7 | Source-backed; follow-up with CIDC |
| 3 | `ABTC1603_treatment` | Trial-constant `AdvtK_Val_Nivo_TMZ` vs Edgar/template blanks | ABTC1603 | treatment | 3 | Source-backed; follow-up with CIDC |

---

## 3. Excluded items

### Non-9-trial items (will be handled in a later workbook/phase)

| Item | Trial(s) | Reason |
|------|----------|--------|
| Cimac.id missing | 10013, 14C0059G | New trials; not in Edgar's 9-trial template |
| Clinical gaps (arm, phase, survival, CE_alt, BOR text) | 10013, 14C0059G | New trials; not in Edgar's 9-trial template |

### Settled or separately handled 9-trial discrepancies (out of scope)

| Item | Trial | Field(s) | Cells | Why excluded |
|------|-------|----------|------:|--------------|
| pfs_bin 120-day landmark (D1) | All 9 trials | pfs_bin | 2,000 | Implemented; confirmation handled separately |
| bor_bin 120-day SD landmark (D2) | All 9 trials | bor_bin | 2,000 | Implemented; confirmation handled separately |
| CRm/CRi → R trade-off (D9) | 10026 | clinical_benefit.binary, bor_bin | 90 | Settled or being handled separately |
| Per-patient OS/PFS anchor (D7) | 10104 | os_time, pfs_time, os_stat, clinical_benefit, clinical_benefit.binary, bor_bin, pfs_bin | 111 | Settled or being handled separately |
| Template anomalies R005–R009 (D12) | 10104 | clinical_benefit, clinical_benefit.binary, os_stat | 43 | Settled or being handled separately |
| E4412 round() vs int() (D10) | CIMAC-e4412 | os_time, pfs_time | 19 | Settled or being handled separately |
| E4412 Unevaluable → other (D11) | CIMAC-e4412 | clinical_benefit, clinical_benefit.binary | 0 | Resolved in 2026-05-20 pass |
| S1400I age integer substitute (D5) | CIMAC-s1400i | age | 511 | Reviewer-approved divergence; settled |
| GU16-257 pfs_time fallback (D13) | CIMAC-gu16257 | pfs_time, pfs_bin | 6 | Settled or being handled separately |
| 10026 other/dash template anomaly | 10026 | clinical_benefit.binary | 18 | Settled or being handled separately |
| 9204 race Other (D14) | CIMAC-9204 | race | 2 | Reviewer-approved divergence; settled |
| 9204 CE_alt Day_8 (D15) | CIMAC-9204 | Collection_Event_alt | 2 | Reviewer-approved divergence; settled |
| 9204 age CD5Z7O5 | CIMAC-9204 | age | 1 | Settled or being handled separately |

---

## 4. Filter logic per worksheet

### Sheet 0: `README_Index`

**Purpose:** Index and legend for the workbook.

**Columns:**
- sheet_name
- example_type
- trial
- field(s)
- n_rows_in_sheet
- n_affected_cells
- slide_reference (which slide in the deck)
- status
- reviewer_decision_or_TODO
- data_source_used
- notes

**Source:** Static; populated from the 3 included worksheet definitions.

---

### Sheet 1: `ABTC1603_pfs_stat`

**Purpose:** All 18 ABTC1603 cells where pfs_stat or pfs_bin mismatches the
template because the pipeline does not count death-without-progression as a
PFS event.

**Slide reference:** Slide 1 — "Possible rule refinements", row: ABTC1603
pfs_stat.

**Source tables:**
1. `harmonization_outputs/validation_report.csv` — mismatch rows
2. `harmonization_outputs/provenance_long.csv` — source file, source column,
   extraction method, confidence, notes
3. `harmonization_outputs/harmonized_9trials_reproduced.csv` — pipeline values
   for context columns (Collection_Event_alt)
4. `cross_trial_analysis_egk_april30_meta_9trials.csv` — Edgar/template values

**Filter logic:**
1. From `validation_report.csv`, select all rows where:
   - `trial = 'ABTC1603'`
   - `column IN ('pfs_stat', 'pfs_bin')`
2. This yields exactly **18 rows** (15 pfs_stat + 3 pfs_bin).
3. For each row, join to `provenance_long.csv` on
   `(trial, cimac_part_id, Cimac.id, Collection_Event)` where
   `harmonized_field = column` to get source_file, source_column,
   extraction_method, confidence, value, notes.
4. Join to `harmonized_9trials_reproduced.csv` on the same key to get
   `Collection_Event_alt`.
5. The 3 pfs_bin rows are downstream of the pfs_stat issue (same patients:
   CG07P2D × 2 timepoints, CG07BWT × 1 timepoint). Include them with a note
   indicating they are downstream cascades.

**Verified mismatch details (from validation_report.csv):**

| field | cimac_part_id | Cimac.id | Collection_Event | template | pipeline | kind |
|-------|---------------|----------|------------------|----------|----------|------|
| pfs_stat | CG07P2D | CG07P2D11.01 | Baseline | 1.0 | 0.0 | numeric_diff |
| pfs_bin | CG07P2D | CG07P2D11.01 | Baseline | 0.0 | (NaN) | missing_in_reproduced |
| pfs_stat | CG07BWT | CG07BWTFY.01 | Baseline | 1.0 | 0.0 | numeric_diff |
| pfs_bin | CG07BWT | CG07BWTFY.01 | Baseline | 0.0 | (NaN) | missing_in_reproduced |
| pfs_stat | CG07P2D | CG07P2DSL.01 | Week_3 | 1.0 | 0.0 | numeric_diff |
| pfs_bin | CG07P2D | CG07P2DSL.01 | Week_3 | 0.0 | (NaN) | missing_in_reproduced |
| pfs_stat | CG07TYT | CG07TYTIZ.01 | Baseline | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07XDN | CG07XDNNF.01 | Baseline | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07TYT | CG07TYTUD.01 | Week_3 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07XDN | CG07XDNOT.01 | Week_3 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07TYT | CG07TYTLF.01 | Week_5 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07XDN | CG07XDNLA.01 | Week_5 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07TYT | CG07TYTS0.01 | Week_11 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG07TYT | CG07TYT3B.01 | Progression | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG078EH | CG078EHQQ.01 | Week_11 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG078EH | CG078EH1C.01 | Baseline | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG078EH | CG078EH3I.01 | Week_3 | 1.0 | 0.0 | numeric_diff |
| pfs_stat | CG078EH | CG078EHB2.01 | Week_5 | 1.0 | 0.0 | numeric_diff |

**Unique patients affected:** 5 (CG07P2D, CG07BWT, CG07TYT, CG07XDN, CG078EH).

**Pattern:** All 15 pfs_stat mismatches share: `Vital Status = DEAD`,
`Days to Progression = NaN`, template `pfs_stat = 1`, pipeline `pfs_stat = 0`.
The 3 pfs_bin mismatches are downstream: pipeline pfs_bin = NaN because
pfs_stat = 0 and pfs_time < 120.

**Level:** Cell-level (one row per mismatching cell).

**Expected rows:** 18.

---

### Sheet 2: `10026_treatment`

**Purpose:** The 7 rows where the pipeline emits the trial-constant
`ipi_aza` but Edgar's template has a blank (NaN) value.

**Slide reference:** Slide 2 — "Template anomalies vs source-backed values",
row: 10026 treatment.

**Source tables:**
1. `harmonization_outputs/validation_report.csv`
2. `harmonization_outputs/provenance_long.csv`
3. `harmonization_outputs/harmonized_9trials_reproduced.csv`
4. `cross_trial_analysis_egk_april30_meta_9trials.csv`

**Filter logic:**
1. From `validation_report.csv`, select all rows where:
   - `trial = '10026'`
   - `column = 'treatment'`
2. This yields exactly **7 rows**.
3. Join to `provenance_long.csv` on the key where
   `harmonized_field = 'treatment'`.
4. Join to `harmonized_9trials_reproduced.csv` for `Collection_Event_alt`.

**Verified mismatch details:**

| cimac_part_id | Cimac.id | Collection_Event | template | pipeline | kind |
|---------------|----------|------------------|----------|----------|------|
| CBUP3C3 | CBUP3C3JV.01 | Baseline | (NaN) | ipi_aza | missing_in_template |
| CBUPJ05 | CBUPJ05P5.01 | Baseline | (NaN) | ipi_aza | missing_in_template |
| CBUPHYS | CBUPHYSKE.01 | Baseline | (NaN) | ipi_aza | missing_in_template |
| CBUPWJU | CBUPWJUD1.01 | Baseline | (NaN) | ipi_aza | missing_in_template |
| CBUPP1Y | CBUPP1Y14.01 | Baseline | (NaN) | ipi_aza | missing_in_template |
| CBUPJUT | CBUPJUTSM.01 | Baseline | (NaN) | ipi_aza | missing_in_template |
| CBUPQS0 | CBUPQS0FK.01 | Baseline | (NaN) | ipi_aza | missing_in_template |

**Pattern:** All 7 rows are `missing_in_template` — the pipeline correctly
emits the trial-constant treatment value; the template left these rows blank.
All are `Baseline` timepoint rows.

**Level:** Cell-level.

**Expected rows:** 7.

---

### Sheet 3: `ABTC1603_treatment`

**Purpose:** The 3 rows where the pipeline emits the trial-constant
`AdvtK_Val_Nivo_TMZ` but Edgar's template has a blank (NaN) value.

**Slide reference:** Slide 2 — "Template anomalies vs source-backed values",
row: ABTC1603 treatment.

**Source tables:** Same as Sheet 2.

**Filter logic:**
1. From `validation_report.csv`, select all rows where:
   - `trial = 'ABTC1603'`
   - `column = 'treatment'`
2. This yields exactly **3 rows**.
3. Join to `provenance_long.csv` and `harmonized_9trials_reproduced.csv`.

**Verified mismatch details:**

| cimac_part_id | Cimac.id | Collection_Event | template | pipeline | kind |
|---------------|----------|------------------|----------|----------|------|
| CG07TB8 | CG07TB82S.01 | Baseline | (NaN) | AdvtK_Val_Nivo_TMZ | missing_in_template |
| CG078BY | CG078BYZ6.01 | Baseline | (NaN) | AdvtK_Val_Nivo_TMZ | missing_in_template |
| CG076LL | CG076LL5B.01 | Baseline | (NaN) | AdvtK_Val_Nivo_TMZ | missing_in_template |

**Pattern:** Same as Sheet 2 — `missing_in_template`. Pipeline uses trial
constant; template left blank.

**Level:** Cell-level.

**Expected rows:** 3.

---

## 5. Standard column layout for example worksheets

Every example worksheet (Sheets 1–3) will include these columns:

| Column | Description |
|--------|-------------|
| `example_type` | Worksheet slug (e.g., `ABTC1603_pfs_stat`) |
| `issue_category` | `rule_refinement` (Sheet 1) or `template_anomaly` (Sheets 2–3) |
| `trial` | Trial name as in harmonized output |
| `field` | Pipeline field name (post-rename: uses `clinical_benefit` / `clinical_benefit.binary` if applicable; not relevant for these 3 sheets) |
| `cimac_part_id` | Patient ID |
| `Cimac.id` | Sample ID |
| `Collection_Event` | Timepoint |
| `Collection_Event_alt` | Alternative timepoint (from harmonized output) |
| `edgar_field` | Edgar's template column name (same as `field` for these 3 sheets — `pfs_stat`, `pfs_bin`, `treatment` are identical in both schemas) |
| `edgar_value` | Value from Edgar's template |
| `pipeline_field` | Same as `field` |
| `pipeline_value` | Value from pipeline output |
| `source_file_path` | From `provenance_long.csv` `source_file` |
| `source_field` | From `provenance_long.csv` `source_column` |
| `source_value` | From `provenance_long.csv` `value` |
| `extraction_method` | From `provenance_long.csv` |
| `confidence` | From `provenance_long.csv` |
| `validation_diff_type` | From `validation_report.csv` `mismatch_kind` |
| `reviewer_decision_TODO` | Reviewer question for this example type |
| `current_status` | `unresolved` (Sheet 1) or `source_backed` (Sheets 2–3) |
| `notes` | Additional context (e.g., "downstream of pfs_stat" for pfs_bin rows) |

**Schema mapping note:** None of the 3 included items involve
`clinical_benefit` / `clinical_benefit.binary`, so the BOR→clinical_benefit
rename does not affect the `field` / `edgar_field` columns in this workbook.
All field names are identical between Edgar's template and the pipeline
output for pfs_stat, pfs_bin, and treatment.

**Reviewer decision/TODO text per sheet:**

- **Sheet 1 (ABTC1603_pfs_stat):** "Should pfs_stat = 1 if Days to
  Progression is present OR Vital Status = DEAD? [follow up with clinical
  team / CIDC]"
- **Sheet 2 (10026_treatment):** "Keep source/config-backed value or
  reproduce Edgar/template blanks? [follow up with CIDC about missing values
  from other fields]"
- **Sheet 3 (ABTC1603_treatment):** Same as Sheet 2.

---

## 6. Implementation approach (for when approved)

The workbook will be generated by a new standalone script:

```
scripts/build_review_workbook.py
```

This script will:
1. Read `validation_report.csv`, `provenance_long.csv`,
   `harmonized_9trials_reproduced.csv`, and
   `cross_trial_analysis_egk_april30_meta_9trials.csv`.
2. For each of the 3 example sheets, apply the filter logic from section 4.
3. Join validation rows to provenance on
   `(trial, cimac_part_id, Cimac.id, Collection_Event, column=harmonized_field)`.
4. Join to the harmonized output for `Collection_Event_alt`.
5. Build the `README_Index` sheet from the worksheet metadata.
6. Write to `harmonization_outputs/clinical_team_review_9trial_current_followup.xlsx`
   using `XlsxWriter` (installed in the venv).
7. Apply light formatting: bold headers, auto-width columns, freeze top row.

**No existing code, config, harmonized CSVs, or generated reports will be
modified.** The script is additive only.

---

## 7. Open questions

None. The scope is well-defined (3 example types, 28 cells, exact filter
logic verified against `validation_report.csv`). No ambiguous classification
or supplementary source file reads are needed — provenance contains all
required source information for these 3 items.
