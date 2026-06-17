# Top remaining review items — with source evidence

Read-only investigation of the **post-120-day-rule** harmonized output. The
recently approved decisions D1 (`bor_bin`), D2 (`pfs_bin`), and D3a
(10026 `CRm`/`CRi` → `R`) are in effect; this report does not relitigate them
except where residual rows remain.

No code, config, or harmonized CSV is modified by this report.

---

## State confirmations (post-rerun)

| Check                                                         | Result                                                                                                  |
|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `harmonized_11trials.csv` row count                           | **2,000** ✓                                                                                              |
| 11 trials registered, BACCI excluded                          | Trials present: 10013, 10026, 10104, 14C0059G, ABTC1603, CIMAC-10021, CIMAC-9204, CIMAC-e4412, CIMAC-gu16257, CIMAC-s1400i, EAY131_Z1D. **0** BACCI rows. |
| `harmonized_12trials.csv`                                     | **Absent** ✓                                                                                             |
| `exclusion_and_order_checks.txt`                              | **VERDICT: PASS — all checks satisfied**                                                                 |
| `bor_bin` / `pfs_bin` provenance                              | Every one of the 2,000 cells per field uses `extraction_method = derived_bor_bin_120d` / `derived_pfs_bin_120d` ✓ |
| `flagged_for_review.csv` rows                                 | **4,542** (was 7,126 pre-rule)                                                                           |
| `validation_report.csv` mismatches vs template                | **836** (per `human_review_summary.txt`)                                                                 |

---

## Part 1 — Prioritized top review items

Ordering reflects: row impact × clinical importance × whether the issue affects
interpretation of `harmonized_11trials.csv`. Mismatch counts are per
`validation_summary.csv` / `validation_report.csv`.

| # | Priority | Trial | Field(s) | Affected | Match rate | Classification | Why it matters |
|---|----------|-------|----------|---------:|-----------:|----------------|----------------|
| 1 | **P1** | CIMAC-s1400i | `age`                                      | 561 | 0.000 | **Missing source file** — decimal age was truncated at the CIDC step | Age is unavailable for 1/4 of the harmonized rows (largest single gap in the dataset). |
| 2 | **P1** | 10013, 14C0059G | `Cimac.id`                              | 219 | n/a (new trials) | **Missing source file** — no sample manifest in either trial directory | Without `Cimac.id`, sample-level joins downstream (CIMAC assay data) are impossible. |
| 3 | **P1** | 10013 | new-trial bulk: `arm`, `phase`, `os_*`, `pfs_*`, `BOR.binary`, `Collection_Event_alt` | up to 196 per field | n/a (new trial) | **Missing source files / source-codebook ambiguity** — no survival, no arm map, free-text BOR | The largest unresolved trial (only ~196 rows but most clinical fields are NA). |
| 4 | **P2** | 10104 | `os_time`                                    | 40 / 213 | 0.812 | **Possible pipeline rule refinement** — anchor-choice mismatch per patient | Survival times disagree with template for 19% of rows; affects OS analysis. |
| 5 | **P2** | 10026 | `BOR.binary` (CRm/CRi pass-through choice)   | 54 / 214 | 0.748 | **Clinical decision** — D3a was chosen; CRm/CRi mismatch is a residual | After D3a, mismatch type is `CRm vs R` and `CRi vs R`; reviewer may want template-byte-fidelity pass-through OR template_anomalies entry. |
| 5 | **P2** | 10026 | `bor_bin` (residual after D3a)               | 36 / 214 | 0.832 | **Clinical decision** — direct consequence of D3a | All 36 mismatches are `template=NaN vs pipeline=1` from the CRm/CRi rows now resolving to `R`. Either accept (rule outperforms template here) or pass-through. |
| 6 | **P2** | 10104 | `os_stat`, `BOR.binary`                     | 17 each | 0.920 each | Mixed: **template anomaly** (CR→NR, PD→R) and source-NaN→template-`other` | Already enumerated in `bor_binary_review_candidates.md` (R005–R009). |
| 7 | **P2** | ABTC1603 | `pfs_stat` (and downstream `pfs_bin`)    | 15 / 148 | 0.899 | **Possible pipeline rule refinement** — pfs_stat does not count death-without-progression as a PFS event | 15 patients have Days-to-Progression=NaN but Vital Status='DEAD'; template counts them as pfs_stat=1, pipeline says 0. |
| 8 | **P2** | 10104 | `pfs_time` (and downstream `bor_bin`, `pfs_bin`) | 14 / 213 | 0.934 | **Possible pipeline rule refinement** — same anchor-choice issue as os_time | Drives 14 pfs_time mismatches and downstream 7 bor_bin + 7 pfs_bin mismatches. |
| 9 | **P3** | CIMAC-e4412 | `pfs_time`, `os_time`                      | 11 + 8 | 0.934 / 0.952 | **Source/pipeline rounding ambiguity** | Off-by-1 days due to `round(months × 30.4375)` rounding direction; minor. |
| 10 | **P3** | CIMAC-e4412 | `BOR`, `BOR.binary`                       | 8 each | 0.952 each | **Source-codebook ambiguity** — `"Unevaluable [<reason>]"` bracketed labels | Already identified as R010 in `bor_binary_review_candidates.md`. |
| 11 | **P3** | 10104 | `BOR`                                       | 9 / 213 | 0.958 | **Template anomalies** (CR→NR, PD→R, etc.) | Per R005–R007, recommendation is to keep pipeline value and add to `template_anomalies.csv`. |
| 12 | **P3** | CIMAC-gu16257 | `pfs_time` and residual `pfs_bin`       | 4 + 2 | 0.980 / 0.990 | **Source-codebook ambiguity** — fallback DFSTIM/DRFSTIM choice on edge cases | Documented in `gu16257_pfs_time_fallback_investigation.md`. |
| 13 | **P3** | 10026 | `treatment`                                | 7 / 214 | 0.967 | Unknown — needs spot-check | 7 of 214 rows differ; low impact. |
| 14 | **P3** | ABTC1603 | `treatment`                              | 3 / 148 | 0.980 | Unknown — needs spot-check | 3 of 148 rows differ; very low impact. |
| 15 | **P3** | CIMAC-9204 | `race`, `Collection_Event_alt`, `age`  | 1–2 each | 0.969–0.985 | **Source-codebook ambiguity** (race=`Other` unmapped) | Tiny; fixable via one-line YAML value-map entries. |

`bor_bin` and `pfs_bin` are now **0** mismatches on six of the nine template
trials and ≥0.97 on the rest; they are no longer the dominant issue and any
remaining residuals trace back to upstream `pfs_time`/`pfs_stat` issues
already listed above.

---

## Part 2 — Source-evidence examples

### Item 1 — CIMAC-s1400i `age` (561 rows, P1)

**Classification:** missing source file (decimal age truncated upstream at CIDC).

**Examples**

| trial | field | cimac_part_id | Cimac.id | Collection_Event | template | pipeline | source file | source column | source value |
|-------|-------|---------------|----------|------------------|---------:|---------:|-------------|---------------|--------------|
| CIMAC-s1400i | age | CCZRBHF | CCZRBHF6N.01 | Baseline      | **50.5** | NaN | `S1400I-clinical/Clinical Dataset 2023_03_14.csv` | `age_num` | `50` |
| CIMAC-s1400i | age | CCZRBHF | CCZRBHF6N.01 | Progression   | **50.5** | NaN | (same row — per-patient, not per-sample) | `age_num` | `50` |
| CIMAC-s1400i | age | CCZRI99 | CCZRI9923.01 | Cycle_5_Week_9| **47.9** | NaN | `S1400I-clinical/Clinical Dataset 2023_03_14.csv` | `age_num` | `47` |
| CIMAC-s1400i | age | CCZR3KB | CCZR3KBHT.01 | Progression   | **83.8** | NaN | (same)                                            | `age_num` | `83` |

**Short quote (codebook):** `S1400I-clinical/CIDC_Annotations_S1400I_20230323.xlsx`, `Sheet1`, rows 2–3 — verbatim:
> "age_num | age_num | **Age truncated** … Age truncated to remove identifying specificity"
> "age_num | age_num | **PHI removed** … changed age > 89 to '90 or older' … PHI"

**Interpretation:** the decimal portion was deliberately removed at the CIDC step
and is **not** recoverable from any file in `S1400I-clinical/`. The template's
decimal age is **per-patient** (constant across all five timepoints for the
same patient), so per-sample collection dates would not let the pipeline
reproduce it either.

**Files checked** (none contain decimal age or sample-collection dates):

- `Clinical Dataset 2023_03_14.csv` (24 cols)
- `Full NGS by alteration.csv` (20 cols)
- `Full NS by patient.csv` (14 cols)
- `TMB PDL1.csv` (3 cols)
- `Toxicity dataset.csv` (4 cols)

**Exact human question:** Can SWOG (the trial sponsor) supply a per-patient
un-truncated `age_decimal` for these 160 patients? If not, accept enrollment-
integer-age as a degraded substitute or accept permanent NA.

---

### Item 2 — 10013 / 14C0059G `Cimac.id` (219 rows, P1)

**Classification:** missing source file (no sample manifest in either trial dir).

**Examples**

| trial | cimac_part_id | Collection_Event   | template | pipeline | source file | source column |
|-------|---------------|--------------------|----------|---------:|-------------|---------------|
| 10013 | CHCO0M4       | Baseline           | (none, new trial) | NaN | (none — no sample-level Cimac.id in any cell of any source file) | n/a |
| 10013 | CHCO0M4       | Definitive Surgery | (none) | NaN | (none) | n/a |
| 10013 | CHCO0M4       | Post Cycle 1       | (none) | NaN | (none) | n/a |
| 14C0059G | CA44RBE     | SCREENING          | (none) | NaN | (none — `research_sample_collection_apheresis.csv` has only `cimac_part_id` and `Days to Sample Collection`) | n/a |
| 14C0059G | CA445VY     | SCREENING          | (none) | NaN | (none) | n/a |

**Short quote (codebook):** `10013-clinical/CIDC_Annotation_2024-11-08.xlsx`, `Annotations` sheet, row 1 — verbatim:
> "Data Element: cimac_part_id … Reason for Transformation: **Added in the
> specimen cimac_id when available**."

**Interpretation:** the CIDC team explicitly states sample IDs were added
"when available" — and for 10013 they are not available in any source file.
For 14C0059G no CIDC annotation file exists, but a brute-force regex scan
(`^C[A-Z0-9]{6,9}$`) of every cell of all 26 source CSVs found only
participant IDs (CA44…). No sample-level CIDC ID anywhere.

**Files checked:** all 28 CSVs in `10013-clinical/`; all 26 CSVs in
`14C0059G-clinical/`; the 3 `CIDC_Annotation*.xlsx` files in 10013-clinical;
`field_locations.docx` in 14C0059G-clinical.

**Exact human question:** Can the CIMAC sample manifest be supplied for each
trial (columns `cimac_part_id`, `Cimac.id`, `Collection_Event`)? If not,
accept permanent NA for sample-level identifiers.

---

### Item 3 — 10013 new-trial bulk flags (up to 196 per field, P1)

**Classification:** mixed — missing source files (survival, arm) and
source-codebook ambiguity (BOR free-text).

**Per-field flagged counts (10013):**

| field                | flagged | reason                                                                    |
|----------------------|--------:|---------------------------------------------------------------------------|
| Cimac.id             |    196  | (Item 2 above)                                                            |
| Collection_Event_alt |    196  | "raw_ce='Baseline': no mapping configured for 10013"                       |
| arm                  |    196  | "10013 arm not derivable from source"                                      |
| phase                |    196  | "10013 phase not derivable from source"                                    |
| os_stat / os_time / pfs_stat / pfs_time | 196 each | "10013 ... not derivable from response file" |
| BOR.binary           |    196  | source `D1` is free-text "Protocol-defined pCR (…)" — no value-map match |
| bor_bin / pfs_bin    |    196 each | downstream of BOR.binary and pfs_time NA                               |

**Example flagged rows (10013):**

| field          | cimac_part_id | candidate_source_variables | observed_source_values                                            | reason                          |
|----------------|---------------|-----------------------------|--------------------------------------------------------------------|---------------------------------|
| BOR.binary     | CHCO0M4       | `BOR`                       | "BOR is NA → BOR.binary NA"                                       | value_NA_at_extraction (0.70)   |
| arm            | CHCO0M4       | `arm`                       | "10013 arm not derivable from source — flag"                       | value_NA_at_extraction (0.50)   |
| os_stat        | CHCO0M4       | `os_stat`                   | "10013 os_stat not derivable from response file — flag"            | value_NA_at_extraction (0.80)   |
| phase          | CHCO0M4       | `phase`                     | "10013 phase not derivable from source — flag"                     | value_NA_at_extraction (0.50)   |
| Collection_Event_alt | CHCO0M4 | `Collection_Event`        | "raw_ce='Baseline': no mapping configured for 10013 (flag)"        | value_NA_at_extraction (0.70)   |

**Short quote (source):** `10013-clinical/response_updated_2024-11-07.csv`,
column `D1` (BOR for 10013), example value (verbatim, abbreviated):
> "Protocol-defined pCR (no residual invasive cancer in the breast or axillary lymph nodes…)"

This long English sentence does not match any code in the global BOR.binary
value-map. The 10013 source has **no** survival columns (no Days-to-Death,
Days-to-Progression, etc.) and **no** arm assignment in any file.

**Files checked:** all 28 CSVs in `10013-clinical/`; `DataDictionary*.xlsx`
files. No survival columns, no arm map, no Collection_Event mapping for the
trial's bucket labels.

**Exact human question:**
1. Should the long pCR text map to `BOR.binary = R` (R011 candidate in `bor_binary_review_candidates.md`, 196 rows)?
2. Can survival data be supplied (NACT trials typically have follow-up CRFs)?
3. Can arm assignment be supplied (or accept "Others")?
4. Can a `Collection_Event_alt` bucket map be supplied for `Baseline / Definitive Surgery / Post Cycle 1` → CIMAC standard timepoints?

---

### Item 4 — 10104 `os_time` (40 / 213 mismatches, P2)

**Classification:** possible pipeline-rule refinement — per-patient anchor
disagreement.

**Mismatch shape (top patterns):**

| template | pipeline | n |
|---------:|---------:|--:|
| 104.0    | 183.0    | 3 |
| 124.0    | 250.0    | 4 |
| 102.0    | 117.0 / 183.0 / 200.0 etc. | several |
| 84.0     | 1037.0   | several (incl. CWWG289) |

**Example: CWWG289**

`provenance_long.csv` says pipeline used column
`"overall survival time in days from first_cycle_first_day to DEATH_DT or
last_follow_up_date" = 1037` in
`10104-clinical/10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv`,
row index 32.

In the **same** source row the patient also has:

> `Days from first_cycle_first_day to tx_phase_end_dt: 84`
> `overall survival time in days from PT_REG_DT_INT to DEATH_DT or last_follow_up_date: 1044`
> `progression free survival time in days from PT_REG_DT_INT to progression_date or DEATH_DT or last_follow_up_date: 63`
> `progression free survival time in days from first_cycle_first_day to progression_date or DEATH_DT or last_follow_up_date: 56`

Template `os_time = 84` matches `Days from first_cycle_first_day to
tx_phase_end_dt`, **not** any survival column. The previously committed P1#1
fix chose `first_cycle_first_day → DEATH_DT or last_follow_up_date` because
it matches the template at ~83%; for these ~17% of patients the template
chose a different anchor (treatment-phase end, or PT_REG_DT for some).

| trial | field | cimac_part_id | Cimac.id      | Collection_Event | template | pipeline | source file | source column | source value |
|-------|-------|---------------|---------------|------------------|---------:|---------:|-------------|---------------|--------------|
| 10104 | os_time | CWWG289     | CWWG2890N.01  | Baseline         | **84**   | 1037   | `10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv` row 32 | (active) `overall survival time … from first_cycle_first_day to DEATH_DT or last_follow_up_date` | `1037` |
| 10104 | os_time | CWWG289     | CWWG2890N.01  | Baseline         | (template 84) | (alt source col) | (same) | `Days from first_cycle_first_day to tx_phase_end_dt`         | `84` |
| 10104 | pfs_time | CWWGSQK    | CWWGSQKVM.01  | Baseline         | **707**  | 966    | (same) | active col                                                   | `966` |

**Interpretation:** the template's OS/PFS anchor varies by patient — likely
crossover / treatment-phase-end cases use `tx_phase_end_dt`, while standard
on-treatment patients use `DEATH_DT or last_follow_up_date`. The pipeline
currently uses a single global rule.

**Exact human question:** Should the 10104 extractor switch to a per-patient
anchor (e.g., use `Days from first_cycle_first_day to tx_phase_end_dt` when
the patient went off treatment but did not die / last follow-up, and survival
columns otherwise)? OR accept the residual mismatches and document as
template anomalies?

---

### Item 5 — 10026 `BOR.binary` residuals after D3a (54 mismatches, P2)

**Classification:** clinical decision pending — D3a chose `CRm`/`CRi` → `R`,
which trades template-byte-fidelity for clinical correctness in the binary
column. The 54 mismatches are the trade-off and are now all of three types:

| template | pipeline | n  | semantics |
|----------|----------|---:|-----------|
| CRm      | R        | 25 | source `CRm` → pipeline maps to `R` (D3a); template kept literal `CRm` |
| CRi      | R        | 11 | same pattern with `CRi`                                                |
| `-`      | NaN      |  2 | source `-` (undefined); pipeline emits NaN; template kept literal `-` (D3b not approved) |
| other    | NaN      | 16 | source blank/MLFS; pipeline emits NaN; template assigned `other` (D3c not approved) |

**Examples:**

| trial | field      | cimac_part_id | Cimac.id      | Collection_Event | template | pipeline | source file                                  | source column | source value |
|-------|------------|---------------|---------------|------------------|----------|----------|----------------------------------------------|---------------|--------------|
| 10026 | BOR.binary | CBUPOJV       | CBUPOJV2D.01  | End_of_Treatment | **CRm**  | R        | `10026-clinical/response_04282024.csv`       | `D3_Alt_1`    | `CRm`        |
| 10026 | BOR.binary | CBUPYC2       | CBUPYC2…      | (any)            | **CRi**  | R        | (same)                                       | `D3_Alt_1`    | `CRi`        |
| 10026 | BOR.binary | CBUPKKC       | …             | (any)            | **`-`**  | NaN      | (same)                                       | `D3_Alt_1`    | `-`          |
| 10026 | BOR.binary | CBUPA3F       | CBUPA3F81.01  | Baseline         | **other**| NaN      | (same)                                       | `D3_Alt_1`    | (blank / `MLFS`) |

**Short quote (codebook):** `10026-clinical/Data_Dictionary.xlsx`, `Sheet1`,
Patient Response Dataset Dictionary, rows 92–94:
> "D3_Alt_1 | BEST_RESPS_ASSMNT_TP_2 | Best overall response | Char | CR | Morphologic Complete Remission"
> "CRi | Morphologic Complete Remission with Incomplete Blood Count Recovery"
> "CRm | Bone Marrow CR"

**Interpretation:** D3a is implemented (CRm/CRi → R). The residual 36 rows
mismatch only because the template keeps the literal short codes. Reviewer
must decide whether to (a) accept the trade-off and add 54 entries to
`template_anomalies.csv`, or (b) switch to pass-through (CRm/CRi/–/other
preserved verbatim), which would restore the BOR.binary match rate to 0.916
but would set the 36 CRm/CRi rows' `bor_bin` back to NaN.

**Exact human question:** keep the D3a R-mapping (and document 54 rows in
`template_anomalies.csv`), or switch to pass-through?

---

### Item 5b — 10026 `bor_bin` residual after D3a (36 mismatches, P2)

**Classification:** direct downstream of D3a. All 36 mismatches are
`template=NaN vs pipeline=1` for the CRm/CRi patients. If D3a's R-mapping is
kept, accept this as a documented trade-off; if D3a switches to pass-through,
the 36 rows revert to NaN and match the template.

---

### Item 6 — 10104 `os_stat` (17) and `BOR.binary` (17), `BOR` (9) (P2)

**Classification:** mix of template anomalies and source-NaN-vs-template-`other`.

**os_stat shape:** all 17 mismatches are `template=0 vs pipeline=1` —
patients where the source `overall survival outcome` field is 1 (event)
but the template says 0 (censored). Per the provenance, the pipeline reads
the source value directly; the template's choice appears to be a different
column.

**BOR / BOR.binary mismatches (examples):**

| template BOR | pipeline BOR | n | cimac_part_id (example) | source value | classification |
|--------------|--------------|--:|--------------------------|--------------|----------------|
| PR           | PD           | 2 | CWWG289                  | `best_response = PD` | template anomaly (R006 in `bor_binary_review_candidates.md`) |
| SD           | PD           | 3 | (several)                | `best_response = PD` | template anomaly (R007) |
| PD           | CR           | 2 | (several)                | `best_response = CR` | template anomaly (R005) |
| PR           | SD           | 2 | (several)                | `best_response = SD` | source ambiguity (R008) |

**Short quote (source):** `10104-clinical/10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv`, column `best_response`. Source value for CWWG289 row 32 (verbatim): `PD`.

**Interpretation:** for 7 of the 9 BOR mismatches the pipeline output is more
clinically consistent than the template (e.g., source PD can't be template R).
These should be added to `template_anomalies.csv` per the existing
recommendation in §2 of `bor_binary_review_candidates.md`.

**Exact human question:** confirm that template_anomalies treatment is correct
for R005–R009, or supply an alternative rule.

---

### Item 7 — ABTC1603 `pfs_stat` (15 mismatches, P2) and downstream `pfs_bin` (3)

**Classification:** possible pipeline-rule refinement.

**All 15 mismatches share the same pattern:**

> `Vital Status = DEAD`, `Days to Progression = NaN`, `Days to Death` non-null.
> Template `pfs_stat = 1` (event), pipeline `pfs_stat = 0` (no progression
> recorded).

**Examples (verbatim source cells):**

| cimac_part_id | Vital Status | Days to Progression | Days to Death | Days to Last Contact | template pfs_stat | pipeline pfs_stat |
|---------------|--------------|---------------------|---------------|----------------------|-------------------|-------------------|
| CG07TYT       | `DEAD`       | NaN                 | `377`         | `377`                | **1**             | 0                 |
| CG078EH       | `DEAD`       | NaN                 | `698`         | `698`                | **1**             | 0                 |
| CG07P2D       | `DEAD`       | NaN                 | `25`          | `25`                 | **1**             | 0                 |
| CG07BWT       | `DEAD`       | NaN                 | `19`          | `19`                 | **1**             | 0                 |
| CG07XDN       | `DEAD`       | NaN                 | `260`         | `260`                | **1**             | 0                 |

**Source file:** `ABTC1603-clinical/abtc_1603_treatmentresponse_03042024_2024-04-17.csv`, columns `Vital Status`, `Days to Progression`, `Days to Death`, `Days to Last Contact`.

**Interpretation:** the pipeline's current rule is
`pfs_stat = 1 iff Days to Progression non-null` (a "progression event only"
convention). The template applies the standard oncology convention
`pfs_stat = 1 iff progression OR death-without-progression` — i.e., death
counts as a PFS event when there is no prior progression. Both conventions
exist; the template's choice is the more common one.

**Exact human question:** approve switching ABTC1603's pfs_stat rule to
`1 iff (Days to Progression non-null) OR (Vital Status = DEAD)`?

---

### Item 8 — 10104 `pfs_time` (14, P2) and downstream `bor_bin`/`pfs_bin` (7 each)

Same root cause as Item 4 (per-patient anchor mismatch). The 14 `pfs_time`
mismatches propagate into 7 `bor_bin` and 7 `pfs_bin` mismatches via the
120-day rule. Fixing Item 4 fixes Item 8 in the same pass.

---

### Item 9 — CIMAC-e4412 `os_time` (8) and `pfs_time` (11) (P3)

**Classification:** rounding ambiguity.

The committed e4412 rule converts source `os_wk` / `pfs_wk` (which encode
months despite the suffix) to days via `round(months × 30.4375)`. All
mismatches are **off-by-1**.

**Examples (verbatim source cells):**

| cimac_part_id | source col | source value | computed days | template days |
|---------------|------------|--------------|---------------|---------------|
| C29ZDAX       | `os_wk`    | `2.97331`    | round(90.51)=**91** | **90** |
| C29ZE03       | `pfs_wk`   | (similar)    | 22                  | 21     |
| (multiple)    | `pfs_wk`   | (similar)    | 34 / 68             | 33 / 67|

**Source file:** `E4412-clinical/baseline_outcomes.xlsx`, sheet `Sheet1`,
columns `os_wk`, `pfs_wk`.

**Interpretation:** the template applies `floor` or `int()` instead of
`round()`. Switching the pipeline to `int(months × 30.4375)` (truncation)
would close most of these.

**Exact human question:** approve switching the e4412 month→day conversion
from `round()` to `int()` truncation?

---

### Item 10 — CIMAC-e4412 `BOR` / `BOR.binary` (8 each, P3)

**Classification:** source-codebook ambiguity (R010 in `bor_binary_review_candidates.md`).

**Examples:**

| template | pipeline | source value (verbatim) | n |
|----------|----------|--------------------------|---|
| other    | `Unevaluable [Scan obtained <6wks(criteria for SD)]` | (same)                  | 3 |
| other    | `Unevaluable [No follow-up dx assessment; patient death]` | (same)              | 1 |
| other    | `Unevaluable [NPT before first dx assessment follow-up]` | (same)               | 1 |
| other    | `Unevaluable [pt went off tx after C1]`              | (same)                  | 2 |
| other    | `Unevaluable [Pt ended tx after C1]`                 | (same)                  | 1 |

**Source file:** `E4412-clinical/baseline_outcomes.xlsx`, column `BEST_OVERALL_RESP_CONF`.

**Exact human question:** approve a `contains: "Unevaluable"` rule for both
`BOR` and `BOR.binary` (BOR→`other`, BOR.binary→`other`)?

---

### Item 11 — 10104 `BOR` template anomalies (9, P3)

Same evidence as the BOR rows of Item 6 (R005–R008 patterns). Recommendation:
add to `template_anomalies.csv`.

---

### Item 12 — CIMAC-gu16257 `pfs_time` (4) and residual `pfs_bin` (2) (P3)

**Classification:** source-codebook ambiguity — fallback DFSTIM/DRFSTIM edge cases.

**Examples:**

| cimac_part_id | Cimac.id      | Collection_Event | template | pipeline | source file                                 | source DFSTIM | source DRFSTIM | source CLCRFL | source RECCUR |
|---------------|---------------|------------------|----------|----------|---------------------------------------------|---------------|----------------|---------------|---------------|
| CM5P4LH       | CM5P4LH9E.01  | C1D1             | **205**  | 253      | `GU16-257-clinical/response.2023-01-04.csv` | `253`         | NaN            | `N`           | `N`           |
| CM5P4LH       | CM5P4LHJH.01  | C3D1             | **205**  | 253      | (same)                                      | `253`         | NaN            | `N`           | `N`           |
| CM5PWSN       | CM5PWSNLN.01  | C1D1             | **NaN**  | 154      | (same)                                      | `154`         | NaN            | `N`           | NaN           |
| CM5PWSN       | CM5PWSNOR.01  | C3D1             | **NaN**  | 154      | (same)                                      | `154`         | NaN            | `N`           | NaN           |

**Interpretation:** for CM5P4LH the template chose 205 while the source has
`DFSTIM=253` and no other plausible PFS column — the source of the 205 is
not obvious. For CM5PWSN the template kept `pfs_time = NaN` while the source
has `DFSTIM=154` — likely because `RECCUR = NaN` (no recurrence status).

**Exact human question:** confirm whether the committed
`pfs_time = DFSTIM if non-null else DRFSTIM` rule should be refined to also
require `RECCUR` to be non-null (would convert the 2 CM5PWSN rows to NaN and
the residual `pfs_bin` mismatches to 0).

---

### Item 13 — 10026 `treatment` (7, P3) and Item 14 — ABTC1603 `treatment` (3, P3)

Low impact; spot-check via `validation_report.csv` filtered by
`(trial, column='treatment')`. Out of scope for this top-items report unless
a reviewer requests escalation.

---

### Item 15 — CIMAC-9204 `race` / `Collection_Event_alt` / `age` (1–2 each, P3)

**race** — 2 rows where template = `unk` but pipeline = NaN.

| cimac_part_id | source col            | source value | template | pipeline |
|---------------|-----------------------|--------------|----------|----------|
| CD5Z9AG       | `itmRace ~ Race`      | `Other`      | **unk**  | NaN      |

**Source file:** `9204-clinical/demographics_dose_level.{ipilimumab|nivolumab}_2024-05-01.csv`.

**Interpretation:** the global value-map has `Unknown → unk` but no
`Other → unk`. One-line YAML addition would close this.

**Collection_Event_alt** — 2 rows where template = `C2` but pipeline =
`Baseline` for `Collection_Event = Day_8`. The 9204 CE-alt-map maps `Day_8 →
Baseline` (per existing notes "only 2 rows"). Template treats these
specifically as `C2`. Minor; a one-line YAML override would close this.

**age** — 1 row (CD5Z7O5): template 68 vs pipeline 64. Both files were checked
and the source has `Age at Enrollment = 64` for ipilimumab vs `Age at
Registration = 68` for nivolumab (most likely; needs spot-confirmation). Probably
a same-patient-in-both-files duplicate where the pipeline picked the wrong file.

---

## Part 3 — Decision summary

| decision_id | priority | issue                                                | trial / field                  | evidence status                                                     | recommended decision                                                                  | what source/documentation is still needed                                  | what to tell Claude if approved                                                                                                                                          |
|-------------|----------|------------------------------------------------------|--------------------------------|---------------------------------------------------------------------|---------------------------------------------------------------------------------------|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D5          | P1       | S1400I `age` decimal lost                            | CIMAC-s1400i / age             | **Strong** (CIDC truncation note)                                   | Supply per-patient un-truncated age, OR substitute `age_num`, OR accept NA            | `S1400I-clinical/age_decimal.csv` from SWOG sponsor                        | (see `source_evidence_decision_memo.md` D5; unchanged)                                                                                                                  |
| D4          | P1       | Missing Cimac.id 10013 / 14C0059G                    | 10013 / 14C0059G / Cimac.id    | **Strong** (CIDC annotation)                                        | Supply external CIMAC sample manifests, OR accept NA                                  | `*-clinical/cimac_manifest.csv` per trial                                  | (see `source_evidence_decision_memo.md` D4; unchanged)                                                                                                                  |
| **D6**      | P1       | 10013 bulk new-trial gaps                            | 10013 / multiple               | **Strong** (no source columns)                                      | Two-step: (i) supply survival + arm + CE-alt map; (ii) approve `Protocol-defined pCR → R` rule | Survival CRFs, arm assignment table, CE-alt mapping; clinical confirmation on pCR-text BOR | "Approved: implement 10013 (a) value_map `'Protocol-defined pCR' → R` via `contains` rule; (b) Collection_Event_alt map `{Baseline→Baseline, Definitive Surgery→EOT, Post Cycle 1→C2}` (confirm with reviewer); add trial_constants for `phase=II`, `arm=Others`; rerun and summarize." |
| **D7**      | P2       | 10104 per-patient OS/PFS anchor                      | 10104 / os_time, pfs_time, os_stat, BOR.binary | **Strong** (CWWG289 shows template=`Days from first_cycle_first_day to tx_phase_end_dt`) | Implement a conditional anchor: use survival columns for on-treatment patients, and `tx_phase_end_dt` for crossover/off-treatment | Confirmation of the per-patient logic (probably based on `Date_of_treatment Cross Over from Arm B to Arm C` non-null) | "Approved: 10104 OS/PFS anchor refinement. For patients with non-null `Date_of_treatment Cross Over from Arm B to Arm C` use `…to tx_phase_end_dt`; else use the current `…to DEATH_DT or last_follow_up_date`. Implement via config + extractor; rerun and summarize." |
| **D8**      | P2       | ABTC1603 pfs_stat counts death-as-event              | ABTC1603 / pfs_stat            | **Strong** (15 patients: Vital Status DEAD, Days to Progression NaN, template pfs_stat=1) | Switch rule to `1 iff (Days to Progression non-null) OR (Vital Status = DEAD)`        | (none — source supports the change)                                        | "Approved: ABTC1603 pfs_stat rule = 1 iff (Days to Progression non-null) OR (Vital Status='DEAD'). Implement via `scripts/extractors/abtc1603.py`; preserve provenance with `extraction_method=derived_pfs_stat_progression_or_death`; rerun and summarize." |
| **D9**      | P2       | 10026 BOR.binary CRm/CRi pass-through vs R           | 10026 / BOR.binary, bor_bin    | **Strong** (D3a in effect; 36 residual CRm/CRi rows)               | **Default:** keep D3a R-mapping and add 54 entries to `template_anomalies.csv`. **Alternative:** switch to pass-through | Reviewer choice                                                            | "Approved: keep CRm/CRi → R; document residual 54 rows in `template_anomalies.csv`." OR "Approved: switch CRm/CRi to pass-through; remove CRm/CRi from the R bucket and re-emit them as their own BOR.binary values; rerun and summarize." |
| **D10**     | P3       | e4412 month→day conversion uses round() vs int()     | CIMAC-e4412 / os_time, pfs_time | **Strong** (all 19 mismatches are off-by-1)                         | Switch from `round()` to `int()` truncation                                           | (none)                                                                     | "Approved: change `round(months × 30.4375)` → `int(months × 30.4375)` in the e4412 time conversion. Implement via `scripts/extractors/e4412.py` (and possibly `s1400i.py` if symmetric); preserve provenance; rerun and summarize." |
| **D11**     | P3       | e4412 BEST_OVERALL_RESP_CONF "Unevaluable […]"       | CIMAC-e4412 / BOR, BOR.binary  | **Strong** (R010)                                                   | Add `contains: "Unevaluable"` rule → `BOR=other, BOR.binary=other`                    | (none)                                                                     | "Approved: in `value_normalizations.BOR` and `BOR.binary`, add a `contains: 'Unevaluable'` rule → `other`. Confidence 0.95. Implement via config; rerun and summarize." |
| **D12**     | P3       | 10104 BOR template anomalies                          | 10104 / BOR (and BOR.binary)   | **Strong** (R005–R007 in `bor_binary_review_candidates.md`)         | Add 7 rows to `template_anomalies.csv`; keep pipeline values                          | (none)                                                                     | "Approved: add 7 R005–R007 rows to `template_anomalies.csv`. No code change; only the anomalies file is updated by the next pipeline run via `generate_review_report.py`." |
| **D13**     | P3       | gu16257 pfs_time fallback edge cases                  | CIMAC-gu16257 / pfs_time, pfs_bin | **Medium** (4 rows; CM5PWSN has RECCUR=NaN)                       | Refine fallback to require RECCUR non-null OR leave as residual                       | Clinical reviewer confirmation                                              | "Approved: gu16257 pfs_time fallback = `DFSTIM if (RECCUR non-null) else (DRFSTIM if non-null else NaN)`. Update extractor; rerun and summarize." |
| **D14**     | P3       | 9204 race `Other → unk`                              | CIMAC-9204 / race              | **Strong** (template carries `unk`)                                 | Add `Other → unk` to `value_normalizations.race`                                      | (none)                                                                     | "Approved: add `Other → unk` (confidence 0.85) to `value_normalizations.race`. One-line YAML; rerun and summarize." |
| **D15**     | P3       | 9204 Collection_Event_alt `Day_8 → C2`                | CIMAC-9204 / Collection_Event_alt | **Strong** (2 rows; template=C2)                                  | Change YAML map for 9204 `Day_8 → C2`                                                 | (none)                                                                     | "Approved: update `9204-clinical.collection_event_alt_map.Day_8` from `Baseline` to `C2`. One-line YAML; rerun and summarize." |
| —           | P3       | 10026 / ABTC1603 treatment residuals (7 / 3)         | 10026, ABTC1603 / treatment    | Pending (out of scope for this report)                              | Spot-check via `validation_report.csv`                                                | TBD                                                                        | TBD                                                                                                                                                                      |

---

## Part 4 — Most important items to discuss with reviewers

In plain language, ranked by what most affects the dataset right now:

1. **S1400I age is missing on 561 rows.** The decimal age the template uses
   was deliberately removed for privacy at the CIDC step. We can either ask
   SWOG for the original un-truncated per-patient age, accept the integer
   enrollment age as a substitute (and note the divergence), or accept that
   age stays blank for this trial. A per-sample collection-date file would
   **not** fix this.

2. **`Cimac.id` is missing for both new trials (10013, 14C0059G).** The CIDC
   team's own annotation says sample IDs were "added when available," and for
   these trials they're not in the source files. We need external CIMAC
   sample manifests — otherwise sample-level joins to assay data are
   impossible for 219 rows.

3. **10013 is mostly blank.** Survival, arm, phase, Collection_Event_alt,
   and BOR are all flagged because the source CSVs lack the necessary
   columns. BOR is free-text ("Protocol-defined pCR (…)") and almost
   certainly maps to `R`, but a clinical reviewer should confirm before we
   commit a `contains: "Protocol-defined pCR"` rule.

4. **10104 survival times differ from the template on ~17% of rows.** The
   template uses a different anchor for some patients (e.g.,
   `tx_phase_end_dt` for those who crossed over or went off treatment).
   Switching to a conditional rule should close ~40 OS-time and ~14
   PFS-time mismatches (and their 7+7 downstream bin mismatches).

5. **ABTC1603 `pfs_stat` is missing the death-as-event case.** 15 patients
   died without a recorded progression date; the template counts them as
   `pfs_stat=1`, the pipeline as 0. This is a one-line rule change with
   strong source support.

6. **10026 `CRm`/`CRi` trade-off.** We already mapped CRm/CRi → R per D3a,
   which fixed the SD-row bin landmarks for 10026 (huge win) but left 54
   `BOR.binary` rows mismatched (template kept the literal short codes). The
   reviewer needs to decide whether to keep R-mapping (and add 54 rows to
   `template_anomalies.csv`) or switch to pass-through.

7. **Small surgical fixes (e4412 rounding, 9204 `Other→unk`, gu16257
   fallback, e4412 `Unevaluable […]`).** Each is a one-line YAML or extractor
   change with strong evidence; bundled, they close ~30 more mismatches and
   move the overall validation rate from 96.9% closer to 99%.

---

## Files referenced

- Outputs: `harmonized_11trials.csv`, `harmonized_9trials_reproduced.csv`,
  `validation_summary.csv`, `validation_report.csv`, `flagged_for_review.csv`,
  `provenance_long.csv`, `source_evidence_report.csv`,
  `review_priority_checklist.csv`, `nonperfect_match_review.md`,
  `final_handoff_report.md`, `human_review_summary.txt`,
  `derived_120d_rules_change_log.md`, `bor_binary_review_candidates.csv`/`md`,
  `gu16257_pfs_time_fallback_investigation.md`.
- Sources: `10026-clinical/response_04282024.csv`,
  `10026-clinical/Data_Dictionary.xlsx`,
  `S1400I-clinical/Clinical Dataset 2023_03_14.csv`,
  `S1400I-clinical/Clinical data dictionary.docx`,
  `S1400I-clinical/CIDC_Annotations_S1400I_20230323.xlsx`,
  `10013-clinical/*` (28 CSVs + `CIDC_Annotation_2024-11-08.xlsx` + `DataDictionary*.xlsx`),
  `14C0059G-clinical/*` (26 CSVs + `field_locations.docx`),
  `10104-clinical/10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv`,
  `ABTC1603-clinical/abtc_1603_treatmentresponse_03042024_2024-04-17.csv`,
  `E4412-clinical/baseline_outcomes.xlsx`,
  `GU16-257-clinical/response.2023-01-04.csv`,
  `9204-clinical/demographics_dose_level.*.csv`.
- No code, config, or harmonized CSV was modified by this report.
