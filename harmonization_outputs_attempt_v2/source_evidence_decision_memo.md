# Reviewer decision memo — CIMAC harmonization

Concise companion to `source_evidence_discrepancy_report.md`. Each item is a single
approval the reviewer needs to make to close the largest remaining gaps in the
harmonized output.

**Scope:** 11 trials (9 template + 2 new). BACCI intentionally excluded.
No code, config, or harmonized CSV is changed by this memo.

---

## D2 — Approve 120-day `pfs_bin` rule

**Rule to approve**

> `pfs_bin = 1` if `pfs_time ≥ 120` days, else `pfs_bin = 0`.
> When `pfs_stat = 0` (censored) and `pfs_time < 120`, emit `NaN`
> (template carries `NaN` for those rows).

**Evidence**

- No source document defines `pfs_bin`. The S1400I and EAY131-Z1D dictionaries
  define only the event flag `pfs_stat`:
  > `S1400I-clinical/Clinical data dictionary.docx`: "ind_pfsrv: Indicator of
  > progression (1) or censored for progression (0)"
  > `EAY131-Z1D-clinical/DataDictionary_*.xlsx`: "pfs_status … 1 if pfs_time is
  > the time of a PFS event"
- Empirical fit against the 9-trial template: across **every** trial with
  non-trivial `pfs_bin`, the max `pfs_time` for `pfs_bin=0` is ≤ 119 and the
  min `pfs_time` for `pfs_bin=1` is ≥ 120 — no overlap. Match rate at 120 d:
  **1.000 on all 8 trials** (10026/10104/10021/s1400i/gu16257/ABTC1603/e4412/Z1D).
  Prior 183-day hypothesis matched only ~81%.

**Current pipeline behavior**

`pfs_bin` is `NaN` for all 2,000 rows; every row is in `flagged_for_review.csv`.

**Recommended decision**

**Approve** the 120-day rule. It is the cleanest derivation supported by the
template; no SAP-level documentation exists to contradict it.

**What to tell Claude if approved**

> "Approved `pfs_bin` rule: `pfs_bin = 1` if `pfs_time ≥ 120`; `pfs_bin = 0` if
> `pfs_time < 120` AND `pfs_stat == 1`; `pfs_bin = NaN` if `pfs_time < 120` AND
> `pfs_stat == 0`. Implement via `harmonization_config.yaml` derived-field
> block + extractor; preserve provenance with
> `extraction_method=derived_pfs_bin_120d`; rerun
> `./scripts/run_full_harmonization.sh`; summarize before/after match rates."

---

## D1 — Approve 120-day `bor_bin` rule

**Rule to approve**

> `bor_bin = 1` if `BOR.binary == 'R'` OR (`BOR.binary == 'SD'` AND `pfs_time ≥ 120`),
> else `bor_bin = 0` (when `BOR.binary` is `NR` or short-PFS `SD`),
> else `NaN` (when `BOR.binary ∈ {other, CRm, CRi, -, NaN}`).

**Evidence**

- No source document defines `bor_bin`. The 10021 variable definitions docx
  defines only the 3-level `ccode` ("Clin-Ben" if CR/PR/SD else "No C-B"),
  not the 2-level `bor_bin`.
- `BOR.binary` alone does not predict `bor_bin`: SD rows split across `bor_bin`
  values within s1400i, 10104, 10026, Z1D. The split is on `pfs_time`.
- Empirical fit against the 9-trial template: at 120 d the rule matches
  **1.000 on all 9 trials** (vs the prior 183-day hypothesis at 0.744–0.860 on
  s1400i / 10026 / Z1D).

**Current pipeline behavior**

`bor_bin` is `NaN` for all 1,781 template rows; 1,376 rows flagged.

**Recommended decision**

**Approve** the 120-day SD-landmark rule. The simplest derivation that
reproduces the template exactly; no SAP-level documentation contradicts it.

**What to tell Claude if approved**

> "Approved `bor_bin` rule: 1 iff `BOR.binary == 'R'` OR
> (`BOR.binary == 'SD'` AND `pfs_time ≥ 120`); 0 iff `BOR.binary == 'NR'` OR
> (`BOR.binary == 'SD'` AND `pfs_time < 120`); `NaN` otherwise. Implement via
> `harmonization_config.yaml` derived-field block + extractor; preserve
> provenance with `extraction_method=derived_bor_bin_120d`; rerun and
> summarize."

---

## D3a — Map 10026 `CRm` and `CRi` to `BOR.binary = R`

**Decision to approve**

> Add `CRm` and `CRi` to the global `BOR.binary` value map so they map to
> **`R`** (responder), based on their data-dictionary definitions as variants
> of Complete Remission.

**Evidence**

- Source file: `10026-clinical/response_04282024.csv`, column `D3_Alt_1`
  ("Best overall response").
- Codebook: `10026-clinical/Data_Dictionary.xlsx`, Sheet1, Patient Response
  Dataset Dictionary, rows 92–94 (verbatim cell contents):
  > "D3_Alt_1 | BEST_RESPS_ASSMNT_TP_2 | Best overall response | Char | CR | Morphologic Complete Remission"
  > "CRi | Morphologic Complete Remission with Incomplete Blood Count Recovery"
  > "CRm | Bone Marrow CR"
- Rows affected: 25 (CRm) + 11 (CRi) = 36 sample rows; 7 patients
  (e.g., `CBUPOJV`, `CBUP58Y`, `CBUPYC2`, `CBUPR3J`).

**Current pipeline behavior**

The YAML map matches only the long form `"CR with MRD-"`, so the literal short
codes `CRm`/`CRi` fall through to `NaN`. The template keeps the literal short
codes in the `BOR.binary` column (preserving an AML-specific subtype rather
than collapsing to `R`).

**Recommended decision**

**Approve mapping CRm → R and CRi → R.** Both are clinically Complete Remission
per the 10026 codebook. Note: this differs from the template, which carries
the literal `CRm`/`CRi` strings; choosing `R` makes `BOR.binary` a true
two/three-level column and feeds correctly into the new `bor_bin` rule
(both will then map to `bor_bin = 1`). If template-byte-fidelity is preferred
instead, request the pass-through variant.

**What to tell Claude if approved**

> "Approved 10026 BOR.binary handling: CRm → R, CRi → R. Add both codes to
> `value_normalizations.BOR.binary` in `harmonization_config.yaml`. Preserve
> provenance with `extraction_method=value_map_global` and a note citing
> the 10026 Data Dictionary rows 92–94. Rerun the wrapper and summarize
> changes to 10026 `BOR.binary` and downstream `bor_bin`."

---

## D3b — Decide how to handle 10026 `"-"`

**Decision to make**

> Keep `BOR.binary = NaN` for the 2 sample rows whose source `D3_Alt_1 = "-"`.

**Evidence**

- Source: `10026-clinical/response_04282024.csv`, `D3_Alt_1 = "-"`
  (1 patient = `CBUPKKC`, 2 sample rows).
- Codebook: `10026-clinical/Data_Dictionary.xlsx` contains **no entry** for
  `"-"`. No quote can be provided — the value is not defined.
- The template preserves the literal `"-"` in `BOR.binary`.

**Current pipeline behavior**

`NaN` for both rows. Flagged.

**Recommended decision**

**Keep `NaN`** (no code change). Mapping `-` to any category (`R`, `NR`, `SD`,
`other`) has no source basis. 2-row impact; documenting this divergence in
`template_anomalies.csv` is sufficient.

Alternative (only if a clinical reviewer states a category): add a one-line
value-map entry and rerun.

**What to tell Claude if approved**

> "Approved: keep `D3_Alt_1='-'` as `BOR.binary=NaN` in 10026. No code
> change. Add a 2-row entry to `template_anomalies.csv` noting that the
> template carries the literal `-` without source basis."

---

## D3c — Confirm: source-blank BOR stays `NaN` (not template-style `other`)

**Decision to make**

> When the source `D3_Alt_1` is blank or contains an out-of-codebook value
> (e.g., `MLFS`), the pipeline emits `BOR.binary = NaN`. The template instead
> assigns `other`. Keep pipeline behavior; do **not** silently invent `other`.

**Evidence**

- Source: `10026-clinical/response_04282024.csv`, `D3_Alt_1` blank (1 patient
  with `MLFS` in source — `MLFS` is not in the 10026 codebook; the row
  collapses to NaN at extraction).
- Rows affected: 16 sample rows (patient `CBUPA3F` and similar).
- Template assigns `BOR.binary = "other"`, but no source value supports it.
- Same pattern appears in 10104 for 8 additional rows (source NaN → template
  `other`); same conservative decision applies there.

**Current pipeline behavior**

`NaN` (correct per the no-silent-guessing policy).

**Recommended decision**

**Confirm `NaN`.** The template's `other` assignment for blank-source rows is
not source-supported; preserving `NaN` is the conservative, traceable choice.
Document in `template_anomalies.csv`.

**What to tell Claude if approved**

> "Approved: preserve `BOR.binary=NaN` for 10026 (and 10104) rows where the
> source `D3_Alt_1`/`best_response` is blank or out-of-codebook. No code
> change. Add a 24-row entry (16 in 10026 + 8 in 10104) to
> `template_anomalies.csv` describing the source-blank → template-`other`
> divergence."

---

## D4 — Confirm: `Cimac.id` for 10013 / 14C0059G requires external manifests

**Decision to make**

> The 219 missing sample-level `Cimac.id` rows (196 in 10013, 23 in 14C0059G)
> cannot be derived from the current source set. Either supply an external
> CIMAC sample manifest per trial, or accept these `Cimac.id` values as
> permanently `NA`.

**Evidence**

- Brute-force regex scan (`^C[A-Z0-9]{6,9}$`) of **every cell in all 28 source
  CSVs in `10013-clinical/`**: every match is a `cimac_part_id` (CHCO-prefixed
  participant ID). No sample-level CIMAC ID appears in any cell.
- Brute-force regex scan of **every cell in all 26 source CSVs in
  `14C0059G-clinical/`**: every match is a `cimac_part_id` (CA44-prefixed).
  No sample-level CIMAC ID in any cell.
- The CIDC team's own annotation confirms the absence
  (`10013-clinical/CIDC_Annotation_2024-11-08.xlsx`, Annotations sheet, row 1):
  > "Data Element: cimac_part_id … Reason for Transformation: **Added in the
  > specimen cimac_id when available**."

**Current pipeline behavior**

All 219 rows have `Cimac.id = NaN` and are in `flagged_for_review.csv` with
`extraction_method = cimac_id_unavailable`, `reason_low_confidence =
value_NA_at_extraction (threshold=1.00)`.

**Recommended decision**

**Confirm: external sample manifests are required.** No other option is
available from the current files.

**What to tell Claude if approved (and manifests supplied)**

> "Supplied CIMAC sample manifests:
> `10013-clinical/cimac_manifest.csv` and
> `14C0059G-clinical/cimac_manifest.csv` with columns `cimac_part_id`,
> `Cimac.id`, `Collection_Event`. Wire each into the corresponding extractor
> (`scripts/extractors/nci_10013.py`, `scripts/extractors/nih_14c0059g.py`)
> with `extraction_method=value_lookup_manifest`. Rerun the wrapper and
> summarize Cimac.id population."

**What to tell Claude if accepted as permanent NA**

> "Accepted: Cimac.id remains NA for 10013 and 14C0059G — no source
> manifest available. Update `final_handoff_report.md` § 3 to mark these
> rows as permanently unresolved, and leave the extraction unchanged."

---

## D5 — Confirm: S1400I age requires per-patient un-truncated age

**Decision to make**

> The S1400I template `age` (decimal) cannot be derived from current source
> files. The correct ask is **per-patient un-truncated decimal age**, not
> per-sample collection dates. Either supply that file, accept the integer
> enrollment age (`age_num`) as a degraded substitute, or accept S1400I `age`
> as permanently `NA`.

**Evidence**

- Source: `S1400I-clinical/Clinical Dataset 2023_03_14.csv`, column `age_num`
  ("Age, years" per data dictionary). All 252 values are integers; max 84
  (because the upstream replaced age > 89 with the string "90 or older").
- The CIDC team's annotation explicitly documents the truncation
  (`S1400I-clinical/CIDC_Annotations_S1400I_20230323.xlsx`, Sheet1, rows 2–3,
  verbatim):
  > "age_num | age_num | **Age truncated** … Age truncated to remove
  > identifying specificity"
  > "age_num | age_num | **PHI removed** … changed age > 89 to '90 or older'
  > … PHI"
- All five S1400I CSVs were scanned for date/collection columns. **None
  exist** (Clinical Dataset, Full NGS by alteration, Full NS by patient,
  TMB PDL1, Toxicity dataset).
- **Crucial:** the template's decimal `age` is **constant per patient**
  across all `Collection_Event` rows (160 of 160 patients have a single
  age value). Example: `CCZRBHF` is `age = 50.5` at Baseline, Cycle_2,
  Cycle_4, Cycle_5, and Progression. So the decimal is per-patient, not
  per-sample, and per-sample collection dates would not let the pipeline
  reproduce the template values.

**Current pipeline behavior**

All 561 S1400I rows have `age = NaN`; flagged.

**Recommended decision**

**Confirm: per-patient un-truncated age is the right ask.** Per-sample
collection dates will **not** help. If un-truncated age is unavailable, the
pragmatic substitute is `age_num` (integer enrollment age) with a documented
divergence; otherwise leave as `NaN`.

**What to tell Claude if approved (and un-truncated age supplied)**

> "Supplied S1400I per-patient un-truncated age at
> `S1400I-clinical/age_decimal.csv` with columns `cimac_part_id`,
> `age_decimal`. Update `scripts/extractors/s1400i.py` to look up
> `age_decimal` by `cimac_part_id` and emit the same value for every
> `Collection_Event` row of that patient, with
> `extraction_method=value_lookup_per_patient`. Rerun and summarize the
> S1400I `age` match rate."

**What to tell Claude if degraded substitute approved**

> "Approved degraded S1400I age: use `age_num` (integer enrollment age) for
> all Collection_Events. Update `scripts/extractors/s1400i.py` accordingly
> with `extraction_method=direct_numeric` and a note explaining the integer
> substitution. Update `final_handoff_report.md` § 3 to document the
> divergence from the template's decimal age."

---

## At-a-glance approvals checklist

| ID  | Decision                                                                       | Impact (rows) | Default recommendation                 |
|-----|--------------------------------------------------------------------------------|---------------|----------------------------------------|
| D2  | Adopt 120-day rule for `pfs_bin`                                                | ~1,781        | **Approve**                            |
| D1  | Adopt 120-day SD-landmark rule for `bor_bin`                                    | ~1,781        | **Approve**                            |
| D3a | Map 10026 `CRm` and `CRi` to `BOR.binary = R`                                   | 36            | **Approve**                            |
| D3b | Keep 10026 `"-"` as `NaN`                                                       | 2             | **Approve** (no code change)           |
| D3c | Keep source-blank BOR as `NaN` (not template-style `other`)                     | 24 (16+8)     | **Approve** (no code change)           |
| D4  | External CIMAC sample manifest is required for 10013 / 14C0059G `Cimac.id`      | 219           | **Approve** (supply manifest OR accept NA) |
| D5  | Per-patient un-truncated age is required for S1400I `age`                       | 561           | **Approve** (supply file OR substitute `age_num` OR accept NA) |

If D1, D2, D3a are all approved, the 9-trial reproduction's three largest open
gaps (1,781 `bor_bin` + 1,781 `pfs_bin` + 36 10026 `BOR.binary`) close in a
single pipeline rerun.
