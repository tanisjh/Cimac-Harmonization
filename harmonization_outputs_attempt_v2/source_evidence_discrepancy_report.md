# Source-evidence discrepancy report

Read-only investigation of the five largest open review areas in the CIMAC clinical
harmonization. For each focus area this report gathers:

- the rows affected and example anchors,
- the source file/column/cell that the template draws from (where one exists),
- a short quote from the source file or data dictionary,
- the template value vs the pipeline value,
- whether the pipeline behavior is source-supported,
- whether the template value is source-supported, ambiguous, or rule-derived,
- the specific human decision required.

**Scope rules**

- No code, config, or harmonized CSV is modified.
- Quotes are intentionally short. CSV/Excel cells and codebook lines are quoted
  verbatim where possible; long Word sections are paraphrased and labelled as
  paraphrase.
- Where no source documentation exists the report says so and lists the files
  that were checked.

**Repository scope:** 11 trials (9 template + 2 new: 10013, 14C0059G); BACCI is
intentionally excluded (`exclusion_and_order_checks.txt` VERDICT: PASS).

---

## Summary of key findings

| # | Focus area              | Rows | Source-doc rule defined?       | Pipeline NA? | Strongest evidence for a rule        |
|---|-------------------------|-----:|--------------------------------|--------------|--------------------------------------|
| 1 | `bor_bin`               | 1781 | **No** — no SAP/codebook       | Yes (all)    | **Empirical 120-day SD landmark matches template at 100% across all 9 trials** (this report, §1) |
| 2 | `pfs_bin`               | 1781 | **No** — no SAP/codebook       | Yes (all)    | **Empirical `pfs_time ≥ 120 days` matches template at 100% across all 8 trials with pfs_bin data** (this report, §2) |
| 3 | 10026 `BOR.binary`      | 54   | Partial (CRm/CRi defined)      | Yes (NA)     | 10026 Data Dictionary defines CRm/CRi as CR variants; template preserves the literal codes |
| 4 | `Cimac.id` 10013        | 196  | n/a — manifest absent          | Yes (all)    | All 28 source CSVs contain only `cimac_part_id`; no sample-level CIMAC ID in any cell |
| 4 | `Cimac.id` 14C0059G     | 23   | n/a — manifest absent          | Yes (all)    | All 26 source CSVs contain only `cimac_part_id`; no sample-level CIMAC ID in any cell |
| 5 | S1400I `age`            | 561  | Source explicitly truncated    | Yes (all)    | S1400I CIDC_Annotations: "Age truncated to remove identifying specificity"; no source file contains per-sample collection dates |

The previously-tested 183-day (6-month) landmark hypothesis that earlier reports cite
(86% / 78% match on s1400i / Z1D) is superseded in this investigation by a
**120-day (≈ 4-month)** landmark that matches at 100% for both `bor_bin` and `pfs_bin`.
This is the single largest evidence change in this investigation and is the basis
for the recommended decisions D1 and D2 below.

---

## 1. `bor_bin` — derivation rule

### 1.1 Rows affected and current behavior

| trial          | rows | template values present                   | pipeline emits |
|----------------|-----:|-------------------------------------------|----------------|
| All 9 template | 1781 | 0 / 1 / NaN (varies by `BOR.binary`)      | NaN (flagged)  |

Flagged in `flagged_for_review.csv`: 1,376 `bor_bin` rows across the 11 trials
(every non-ABTC1603 row). ABTC1603 is template-constant NaN; the pipeline matches.

### 1.2 Is the rule defined in any source document?

**No.** The following documents were searched for the keywords `bor_bin`,
`bor binary`, `clinical benefit`, `landmark`, `derived`, `6-month`, `4-month`:

- `10021-clinical/10021_Variable_Definitions.docx` — defines `rcode` and `ccode` only:
  > "Disease control classification ccode: if BEST_RESPS_ASSMNT_TP_2_STD in ('CR','PR','SD') then ccode = 'Clin-Ben'; else ccode = 'No C-B'"
  This is a 3-category clinical-benefit indicator, not the 2-level `bor_bin`.
- `S1400I-clinical/Clinical data dictionary.docx` — defines `ind_pfsrv` and `indo_osrv`; **no `bor_bin` definition**.
- `EAY131-Z1D-clinical/DataDictionary_VariableList_DR-MATCH-0028-CS-0005.xlsx` — defines `pfs_status` (0/1 event flag); **no `bor_bin`**.
- `10026-clinical/Data_Dictionary.xlsx`, `10013-clinical/DataDictionary_*.xlsx`, `GU16-257-clinical/data_dictionary.2023-01-19.xlsx`, `14C0059G-clinical/field_locations.docx` — none define `bor_bin`.

### 1.3 Why `BOR.binary` alone does not predict `bor_bin`

In the template, `BOR.binary` ∈ {R, NR, SD, other, NaN, plus 10026-specific CRm/CRi/-}.
Across all 9 trials, `bor_bin` is deterministic given `BOR.binary` **except for SD rows**,
which split:

```
trial         BOR.binary=SD : (bor_bin=0, bor_bin=1, NaN)
CIMAC-s1400i  (96, 163, 0)
10104         (33, 54, 0)
10026         (23, 70, 0)
EAY131_Z1D    (3, 15, 0)
CIMAC-e4412   (14, 0, 0)      ← all SD → 0 (no SD reaches landmark)
CIMAC-9204    (0, 0, 28)      ← SD always NaN
```

This rules out any rule that uses `BOR.binary` alone.

### 1.4 The 120-day SD landmark explains the SD split

Among SD rows, sorting by `pfs_time` shows a sharp cutoff:

| trial         | SD with bor_bin=0: max pfs_time | SD with bor_bin=1: min pfs_time |
|---------------|---------------------------------:|---------------------------------:|
| 10026         | 106 d                            | 120 d                            |
| 10104         | 119 d                            | 151 d                            |
| CIMAC-s1400i  | 119 d                            | 127 d                            |
| EAY131_Z1D    | 106 d                            | 163 d                            |

There is no overlap between the two groups in any trial. The boundary lies in the
[107, 120] window, consistent with a **120-day landmark**.

Concrete examples (all sample timepoints share the patient-level pfs_time/bor_bin):

| trial   | cimac_part_id | BOR.binary | pfs_time | pfs_stat | bor_bin |
|---------|---------------|-----------|---------:|---------:|--------:|
| CIMAC-s1400i | CNKA2VG  | SD        |  112     | 1        | 0       |
| CIMAC-s1400i | CNKAGQM  | SD        |  119     | 1        | 0       |
| 10104   | CWWG9X0       | SD        |  119     | 1        | 0       |
| 10104   | CWWGYRB       | SD        |  151     | 1        | 1       |

### 1.5 Candidate rule and match rate

Rule tested:

```
bor_bin = 1   iff   BOR.binary == 'R'   OR   (BOR.binary == 'SD' AND pfs_time ≥ 120 days)
bor_bin = 0   iff   BOR.binary == 'NR'  OR   (BOR.binary == 'SD' AND pfs_time <  120 days)
bor_bin = NaN otherwise (BOR.binary ∈ {other, CRm, CRi, -, NaN})
```

Match rate against the template, by trial (rows with non-NaN template `bor_bin`):

| trial         | n_valid | match @ 120 d | match @ 183 d (prior hypothesis) |
|---------------|--------:|--------------:|--------------------------------:|
| CIMAC-9204    | 36      | 1.000         | 1.000                            |
| CIMAC-e4412   | 159     | 1.000         | 1.000                            |
| CIMAC-s1400i  | 561     | **1.000**     | 0.857                            |
| CIMAC-10021   | 154     | 1.000         | 1.000                            |
| CIMAC-gu16257 | 190     | 1.000         | 1.000                            |
| 10104         | 205     | **1.000**     | 0.951                            |
| 10026         | 160     | **1.000**     | 0.744                            |
| EAY131_Z1D    | 57      | **1.000**     | 0.860                            |

The 120-day rule reproduces the template at **100% across all 9 trials**.
ABTC1603 is excluded (template-constant NaN; rule emits NaN by construction).

### 1.6 Source-supported?

- **Pipeline NA:** source-supported under the no-silent-guessing policy
  (`provenance_long.csv` shows `extraction_method=derived_bor_binary_no_BOR` /
  flagged at confidence 0.0).
- **Template `bor_bin`:** **rule-derived**, with **no source document defining
  the rule**. The empirical fit is exact at 120 days but the threshold itself
  is not documented in any data dictionary in the repository.

### 1.7 Human decision required

**D1:** Confirm the 120-day SD-landmark rule (or supply the actual SAP rule).
A single YAML edit + extractor change can populate ~1,500 template rows and
the equivalent rows for the two new trials.

---

## 2. `pfs_bin` — derivation rule

### 2.1 Rows affected and current behavior

| trial          | rows | template values | pipeline emits |
|----------------|-----:|-----------------|----------------|
| All 9 template | 1781 | 0 / 1 / NaN     | NaN (flagged)  |

Flagged in `flagged_for_review.csv`: 2,000 `pfs_bin` rows across the 11 trials.

### 2.2 Is the rule defined in any source document?

**No.** Searched the same documents as §1.2. The closest references are simple
event indicators:

- `EAY131-Z1D-clinical/DataDictionary_VariableList_DR-MATCH-0028-CS-0005.xlsx`:
  > "pfs_status … 1 if pfs_time is the time of a PFS event"
  > "pfs_status … 0 if pfs_time is the time last known a PFS had not occurred"
- `S1400I-clinical/Clinical data dictionary.docx`:
  > "ind_pfsrv: Indicator of progression (1) or censored for progression (0)"

These define the 0/1 event flag (`pfs_stat`), **not** the binary `pfs_bin`
landmark indicator.

### 2.3 Why `pfs_stat` alone does not predict `pfs_bin`

```
trial         pfs_stat=0 → pfs_bin   pfs_stat=1 → pfs_bin
CIMAC-s1400i  (0, 41, 4)              (276, 240, 0)
10104         (0, 10, 3)              (104, 95,  0)
10026         (0, 10, 2)              ( 52, 134, 0)
EAY131_Z1D    (0, 17, 4)              ( 20, 22,  0)
```

So `pfs_bin` is not a copy of `pfs_stat`.

### 2.4 The 120-day rule explains `pfs_bin`

Across every trial, `pfs_time` sorted by `pfs_bin` shows the same boundary:

| trial         | pfs_bin=0 max pfs_time | pfs_bin=1 min pfs_time |
|---------------|----------------------:|------------------------:|
| 10026         | 107 d                  | 120 d                   |
| 10104         | 119 d                  | 151 d                   |
| CIMAC-10021   | 116 d                  | 120 d                   |
| CIMAC-s1400i  | 119 d                  | 122 d                   |
| ABTC1603      | 99 d                   | 139 d                   |
| EAY131_Z1D    | 106 d                  | 163 d                   |
| CIMAC-gu16257 | 95 d                   | 137 d                   |

No overlap in any trial. CIMAC-9204 has `pfs_bin` NaN for all rows and is
excluded.

### 2.5 Candidate rule and match rate

Rule tested:

```
pfs_bin = 1   if pfs_time ≥ 120 days
pfs_bin = 0   if pfs_time <  120 days AND pfs_stat == 1 (event observed)
pfs_bin = NaN if pfs_time <  120 days AND pfs_stat == 0 (censored short)
```

Match rate against the template (rows with non-NaN template `pfs_bin`):

| trial         | n_valid | match @ 120 d | match @ 183 d (prior hypothesis) |
|---------------|--------:|--------------:|--------------------------------:|
| 10026         | 196     | **1.000**     | ~0.81                            |
| 10104         | 209     | **1.000**     | ~0.81                            |
| ABTC1603      | 145     | 1.000         | ~                                |
| CIMAC-10021   | 153     | 1.000         | ~                                |
| CIMAC-e4412   | 74      | 1.000         | ~                                |
| CIMAC-gu16257 | 193     | 1.000         | ~                                |
| CIMAC-s1400i  | 557     | **1.000**     | ~0.81                            |
| EAY131_Z1D    | 59      | **1.000**     | ~0.81                            |

The 120-day rule reproduces the template at **100% across all 8 trials with
non-trivial `pfs_bin`**.

### 2.6 Source-supported?

- **Pipeline NA:** source-supported under the uncertainty policy.
- **Template `pfs_bin`:** rule-derived with **no source document defining the
  threshold**. The empirical fit is exact at 120 days but the rule is not
  documented in any data dictionary in the repository.

### 2.7 Human decision required

**D2:** Confirm the 120-day landmark for `pfs_bin` (or supply the actual SAP
rule). One YAML/extractor edit can populate ~1,700 template rows plus
equivalent rows in the two new trials.

---

## 3. 10026 `BOR.binary` (match 0.748)

### 3.1 Rows affected

214 sample rows total, of which **54 disagree** with the template:

| source D3_Alt_1 | n participants | n template rows | template `BOR.binary` | pipeline `BOR.binary` | mismatch? |
|-----------------|--------------:|----------------:|-----------------------|-----------------------|-----------|
| CR              | 9             | 41              | R                     | R                     | match     |
| SD              | 22            | 93              | SD                    | SD                    | match     |
| PD              | 7             | 26              | NR                    | NR                    | match     |
| CRm             | 6 (1 NaN)     | 25              | `CRm` (literal)       | NaN                   | **mismatch (25)** |
| CRi             | 2             | 11              | `CRi` (literal)       | NaN                   | **mismatch (11)** |
| `-`             | 1             | 2               | `-` (literal)         | NaN                   | **mismatch (2)**  |
| (source NaN)    | 1 (MLFS)      | 16              | `other`               | NaN                   | **mismatch (16)** |

(Patient count expands to 214 sample rows because each patient has multiple
`Collection_Event` rows in the template.)

### 3.2 Source file

- **Source CSV:** `10026-clinical/response_04282024.csv`
- **Column:** `D3_Alt_1` (a.k.a. `BEST_RESPS_ASSMNT_TP_2`) — "Best overall response"
- **Data dictionary:** `10026-clinical/Data_Dictionary.xlsx`, sheet `Sheet1`,
  Patient Response Dataset Dictionary, row 92–94. Verbatim cells:

  > `D3_Alt_1 | BEST_RESPS_ASSMNT_TP_2 | Best overall response | Char | CR | Morphologic Complete Remission`
  > `CRi | Morphologic Complete Remission with Incomplete Blood Count Recovery`
  > `CRm | Bone Marrow CR`

- **D3_Alt_1 source value counts:** SD 22, CR 9, PD 7, CRm 6, CRi 2, `-` 1, MLFS 1
  (48 source rows, mapped to 214 sample timepoints).

### 3.3 Concrete example rows

| cimac_part_id | source D3_Alt_1 | template BOR | template BOR.binary | template bor_bin | pipeline BOR.binary |
|---------------|-----------------|--------------|---------------------|------------------|---------------------|
| CBUPZKW       | CR              | CR           | R                   | 1                | R (match)           |
| CBUPTMN       | PD              | PD           | NR                  | 0                | NR (match)          |
| CBUPBR1       | SD              | SD           | SD                  | 0                | SD (match)          |
| CBUPOJV       | CRm             | CRm          | **CRm**             | NaN              | **NaN**             |
| CBUP58Y       | CRm             | CRm          | **CRm**             | NaN              | **NaN**             |
| CBUPYC2       | CRi             | CRi          | **CRi**             | NaN              | **NaN**             |
| CBUPR3J       | CRi             | CRi          | **CRi**             | NaN              | **NaN**             |
| CBUPKKC       | `-`             | `-`          | **`-`**             | NaN              | **NaN**             |
| CBUPA3F       | (NaN, MLFS)     | NaN          | **`other`**         | NaN              | **NaN**             |

(`flagged_for_review.csv` confirms all 54 rows are at confidence 0.0 with
`reason_low_confidence = value_NA_at_extraction (threshold=0.70)`.)

### 3.4 Interpretation per source value

**CRm (25 sample rows / 5 patients)** — source-supported and unambiguous.
The data dictionary defines `CRm = "Bone Marrow CR"`. The template preserves
the literal short code in `BOR.binary` rather than collapsing to R. The
pipeline emits NaN because the YAML map does not include the short form
(only the long-form `"CR with MRD-"`). **Safe to add via config**:
either pass-through (CRm → CRm) to match template, or map (CRm → R) on
clinical grounds. Template fidelity favors pass-through.

**CRi (11 sample rows / 2 patients)** — same situation as CRm. Data dictionary:
`CRi = "Morphologic Complete Remission with Incomplete Blood Count Recovery"`.
**Safe to add via config** (pass-through preferred for template fidelity).

**`-` (2 sample rows / 1 patient)** — source-ambiguous. The dash is **not
defined** in the 10026 Data Dictionary. The template preserves the literal
`-`. **Low impact (2 rows). Recommend keeping NaN unless a clinical reviewer
confirms a category** — there is no source basis to map it to R/NR/SD/other.

**Source NaN → template `other` (16 sample rows / 1 patient — MLFS at source)**
— template-divergent. The source has `D3_Alt_1 = NaN` for this patient (one
row shows `MLFS` which is not in any 10026 data-dictionary code list). The
template assigns `other` without source basis. **Recommend preserving NaN**;
the template's choice of `other` for blank-source rows is not source-supported.
This pattern (`R004` in `bor_binary_review_candidates.md`) is the same as the
24 source-NaN-vs-template-`other` rows seen in 10104.

### 3.5 Source-supported?

- **Pipeline NA**: source-supported under uncertainty policy (codes not in the global YAML map).
- **Template values**: `CRm`/`CRi` literals **are source-supported** (data
  dictionary defines them); `-` is **not source-defined**; the `other`
  assignment for source-NaN is **not source-supported**.

### 3.6 Human decision required

**D3a:** approve CRm/CRi pass-through (or R-mapping) — 36 rows.
**D3b:** decide `-` (likely keep NaN) — 2 rows.
**D3c:** confirm source-NaN → NaN (not `other`) for the 16-row patient — 16 rows.

---

## 4. Missing `Cimac.id` for 10013 and 14C0059G

### 4.1 Rows affected

| trial    | rows in 11trials.csv | distinct cimac_part_id | Cimac.id non-null |
|----------|---------------------:|-----------------------:|------------------:|
| 10013    | 196                  | 51                     | **0**             |
| 14C0059G | 23                   | 15                     | **0**             |

219 rows total are NA + flagged in `flagged_for_review.csv` with
`reason_low_confidence = value_NA_at_extraction (threshold=1.00)` and
`extraction_method = cimac_id_unavailable`.

### 4.2 Source files checked

**10013** — all 28 CSVs were scanned for any cell matching the CIDC sample-ID
pattern `^C[A-Z0-9]{6,9}$`. **Every hit was a `cimac_part_id`** (CHCO* prefix);
no sample-level CIMAC ID was found in any cell of any file:

```
additional_treatment_2023-05-22.csv      → cimac_part_id only (671 hits, all CHCO*)
adverse_event_2023-09-13.csv             → cimac_part_id only (2051 hits)
specimen_collection_2023-09-13.csv       → cimac_part_id only (789 hits)
response_updated_2024-11-07.csv          → cimac_part_id only (51 hits)
... (all 28 files)
```

`specimen_collection_2023-09-13.csv` is the file that would normally carry a
sample identifier; its columns are `M6, M7, M2, M4, cimac_part_id` — all five
sample fields are either coded data (specimen type, timepoint, etc.) or the
participant ID. No CIMAC sample ID column exists.

**14C0059G** — all 26 CSVs were scanned. Every match for the CIDC pattern is
a `cimac_part_id` (CA44* prefix); **no sample-level CIMAC ID was found** in
any cell:

```
research_sample_collection_apheresis.csv → cimac_part_id (21), Days to Sample Collection
patient_demographics_all.csv             → cimac_part_id only
all_labs.csv                             → cimac_part_id only (31,985 hits)
... (all 26 files)
```

The file `research_sample_collection_apheresis.csv` is the closest analogue to
a sample manifest; it carries `cimac_part_id` and `Days to Sample Collection`
but **no sample-level Cimac.id column**.

### 4.3 Data-dictionary / annotation quotes

- **10013** `CIDC_Annotation_2024-11-08.xlsx`, sheet `Annotations`, row 1
  (verbatim):
  > "Data Element: cimac_part_id … Reason for Transformation: **Added in the
  > specimen cimac_id when available**."

  → The CIDC team explicitly states they added the sample ID **when
  available** — and for 10013 it is not available in any source file.

- **14C0059G** has no CIDC_Annotation file; `field_locations.docx` documents
  field locations only (CRF page numbers), not sample IDs.

### 4.4 Example rows

| trial    | cimac_part_id | Collection_Event   | source `Cimac.id` candidate | pipeline `Cimac.id` |
|----------|---------------|--------------------|------------------------------|---------------------|
| 10013    | CHCO0M4       | Baseline           | (absent — no column anywhere) | NaN                 |
| 10013    | CHCO0M4       | Definitive Surgery | (absent)                     | NaN                 |
| 10013    | CHCO0M4       | Post Cycle 1       | (absent)                     | NaN                 |
| 14C0059G | CA44RBE       | SCREENING          | (absent — no column anywhere) | NaN                 |
| 14C0059G | CA44RBE       | DAY 60             | (absent)                     | NaN                 |
| 14C0059G | CA445VY       | SCREENING          | (absent)                     | NaN                 |

### 4.5 Source-supported?

- **Pipeline NA:** **strongly source-supported.** No source column or source
  cell contains a sample-level CIMAC ID in either trial. The CIDC annotation
  for 10013 explicitly confirms the absence.
- **Template:** template does not cover these two trials (they are new).
  No template ground truth exists.

### 4.6 Human decision required

**D4:** Either (a) supply external CIMAC sample manifests
(`10013-clinical/cimac_manifest.csv` and
`14C0059G-clinical/cimac_manifest.csv`, with columns
`cimac_part_id`, `Cimac.id`, `Collection_Event`) and reprocess, or
(b) accept `Cimac.id` as permanently NA for these trials. No third option
is available from the current source set.

---

## 5. S1400I `age` (match 0.000, 561 rows)

### 5.1 Rows affected

All 561 S1400I sample rows have template `age` ∈ {decimal years} but pipeline
emits NaN, since the pipeline cannot derive the decimal portion from any
source file.

### 5.2 Source file and explicit truncation note

- **Source CSV:** `S1400I-clinical/Clinical Dataset 2023_03_14.csv`
- **Source column:** `age_num` ("Age, years, Num" per data dictionary)
- **Data dictionary** (`S1400I-clinical/Clinical data dictionary.docx`, verbatim):
  > "age_num | Age, years | Num"

  No decimal-year column is defined.

- **CIDC_Annotations_S1400I_20230323.xlsx**, sheet `Sheet1`, rows 2 and 3
  (verbatim cell contents):
  > "age_num | age_num | **Age truncated** … Age truncated to remove identifying specificity"
  > "age_num | age_num | **PHI removed** … changed age > 89 to '90 or older' … PHI"

  → The source explicitly states that `age_num` was **truncated to integer
  years** as a privacy step.

### 5.3 Source values

```
age_num: integer years (e.g., 65, 73, 83, 72, 66); min=41, max=84;
         100% of non-null values are integers; ages > 89 replaced with "90 or older" string.
```

### 5.4 Template values

```
template age (CIMAC-s1400i, first 6 rows): 50.5, 47.9, 79.3, 73.7, 83.8, 72.6 …
```

- All template values are decimal.
- `(template age − source age_num)` is uniformly in [0.0, 0.9] across 561 rows
  (mean 0.48, std 0.27). This is the fractional year that was removed at
  truncation.

### 5.5 Crucial: template decimal-age is per-patient, **not** per-sample

For all 160 S1400I patients, the template stores **a single age value per patient**
(0 patients have more than one distinct `age` across timepoints). Example:

| cimac_part_id | Collection_Event   | template age | source age_num |
|---------------|--------------------|-------------:|---------------:|
| CCZRBHF       | Baseline           | 50.5         | 50             |
| CCZRBHF       | Cycle_2_Week_3     | 50.5         | 50             |
| CCZRBHF       | Cycle_4_Week_7     | 50.5         | 50             |
| CCZRBHF       | Cycle_5_Week_9     | 50.5         | 50             |
| CCZRBHF       | Progression        | 50.5         | 50             |

This contradicts the earlier hypothesis ("template age = per-sample age at
collection"): the template is **not** computing a per-sample collection-date
age — it is preserving an un-truncated per-patient decimal that the CIMAC
pipeline removed for PHI. There is no per-sample component to recover.

### 5.6 Are sample collection dates present anywhere?

**No.** All five S1400I source CSVs were inspected for any column matching
`date | dt | dob | birth | collect | visit | reg | sample | draw | enrol`:

| file                                             | n_cols | date/collection columns |
|--------------------------------------------------|------:|-------------------------|
| Clinical Dataset 2023_03_14.csv                  | 24    | (none)                  |
| Full NGS by alteration.csv                       | 20    | (none)                  |
| Full NS by patient.csv                           | 14    | (none)                  |
| TMB PDL1.csv                                     | 3     | (none)                  |
| Toxicity dataset.csv                             | 4     | (none)                  |

`flagged_for_review.csv` corroborates this:

> "Source age_num is age at enrollment (integer); template uses age at sample
> collection (decimal)"

(The flag message is slightly stronger than the source supports — the
template's age is actually per-patient decimal, not per-sample.)

### 5.7 Source-supported?

- **Pipeline NA:** source-supported. The decimal portion was deliberately
  removed at the CIDC step and cannot be recovered from the released files.
- **Template decimal age:** comes from an un-truncated upstream age value
  that is **not present in the CIDC release**. The template's age is
  source-supported in principle (it is real per-patient decimal age from
  the SWOG sponsor) but is **not reproducible from any file in the current
  repository**.

### 5.8 Human decision required

**D5:** Either (a) supply the original un-truncated `age` from SWOG as a new
per-patient file (e.g., `S1400I-clinical/age_decimal.csv` with columns
`cimac_part_id`, `age_decimal`), or (b) accept that the pipeline reports the
integer enrollment age (degraded substitute) and document the divergence, or
(c) accept S1400I `age` as permanently NA.

A per-sample collection-date file is **not** the right ask: the template's
age is per-patient, not per-sample, so collection dates would not let the
pipeline reproduce the template values.

---

## 6. Separation of source-supported vs unresolved rule items

| Issue                              | Pipeline behavior              | Source-supported? | Template value status                  |
|------------------------------------|--------------------------------|-------------------|-----------------------------------------|
| 1. `bor_bin` (1,781 rows)          | NA + flagged                   | Yes (uncertainty policy) | Rule-derived; **no source-doc rule**; empirically reproduced @ 120 d, 100% |
| 2. `pfs_bin` (1,781 rows)          | NA + flagged                   | Yes (uncertainty policy) | Rule-derived; **no source-doc rule**; empirically reproduced @ 120 d, 100% |
| 3a. 10026 BOR.binary CRm (25 rows) | NA                             | YAML map gap, not policy | Source-supported (data dictionary)      |
| 3b. 10026 BOR.binary CRi (11 rows) | NA                             | YAML map gap, not policy | Source-supported (data dictionary)      |
| 3c. 10026 BOR.binary `-` (2 rows)  | NA                             | YAML map gap      | **Not source-defined** in data dictionary |
| 3d. 10026 BOR.binary source-NaN (16 rows) | NA                      | Source has no value | Template assigns `other` **without source basis** |
| 4. 10013 / 14C0059G Cimac.id (219) | NA + flagged                   | Yes (source absent) | n/a (no template ground truth)         |
| 5. S1400I age (561)                | NA + flagged                   | Yes (source truncated) | Source-supported upstream; **not reproducible** from current files |

---

## 7. Reviewer decision summary

| decision_id | issue                              | evidence status                            | recommended decision (after this evidence)        | what source/documentation is still needed (if any) | what to tell Claude if approved                                                                 |
|-------------|------------------------------------|--------------------------------------------|---------------------------------------------------|--------------------------------------------------|-------------------------------------------------------------------------------------------------|
| D1          | `bor_bin` derivation rule          | **Strong** — empirical 100% match @ 120 d  | Adopt 120-day SD landmark rule                    | (optional) the analysis SAP if available, to confirm threshold | "Approved `bor_bin` rule: 1 iff BOR.binary=='R' OR (BOR.binary=='SD' AND pfs_time≥120). Implement via `harmonization_config.yaml` derived_bor_bin block + extractor; preserve provenance with `extraction_method=derived_bor_bin_rule_120d`; rerun the wrapper; summarize before/after match rates." |
| D2          | `pfs_bin` derivation rule          | **Strong** — empirical 100% match @ 120 d  | Adopt 120-day landmark for pfs_bin                | (optional) the analysis SAP                      | "Approved `pfs_bin` rule: 1 iff pfs_time≥120; 0 iff pfs_time<120 AND pfs_stat==1; NaN iff pfs_time<120 AND pfs_stat==0. Implement via config + extractor; preserve provenance; rerun and summarize." |
| D3a         | 10026 BOR.binary CRm / CRi         | **Strong** — data dictionary defines codes | Pass-through CRm/CRi (template fidelity) OR map to R (clinical fidelity) | A reviewer choice between template-faithful pass-through vs binary R-mapping | "Approved 10026 BOR.binary handling: <pass-through OR R-mapping>. Add CRm and CRi to `value_normalizations.BOR.binary` accordingly; rerun and summarize." |
| D3b         | 10026 BOR.binary `-` (2 rows)      | **Weak** — `-` not in data dictionary       | Keep NaN unless clinical reviewer confirms        | Clinical meaning of `-` in 10026 response file   | "Approved: keep `-` as NaN in 10026 BOR.binary (template carries the literal but source basis is undefined). No code change."  |
| D3c         | 10026 BOR.binary source-NaN→`other`(16) | Source-unsupported template assignment | Preserve NaN (do not invent `other`)              | (none — already source-supported)                | "Approved: preserve NaN where 10026 source BOR is blank/MLFS; document the 16-row template divergence in `template_anomalies.csv`."  |
| D4          | 10013 / 14C0059G Cimac.id (219)    | **Strong** — source ID is absent           | Either supply external manifests OR accept NA     | External CIMAC sample manifest per trial         | "Supplied CIMAC sample manifest at `10013-clinical/cimac_manifest.csv` and `14C0059G-clinical/cimac_manifest.csv` with columns `cimac_part_id`, `Cimac.id`, `Collection_Event`. Wire into the respective extractors; rerun and summarize." |
| D5          | S1400I `age` (561)                 | **Strong** — source explicitly truncated   | Either supply un-truncated per-patient age OR accept enrollment-integer-age substitute OR NA | Per-patient un-truncated decimal age from SWOG sponsor (NOT per-sample collection dates) | "Supplied S1400I per-patient un-truncated age at `S1400I-clinical/age_decimal.csv` with columns `cimac_part_id`, `age_decimal`. Add a derivation in the S1400I extractor that joins on cimac_part_id and emits the decimal age for every Collection_Event row; rerun and summarize." |

---

## 8. Files referenced by this report

| File                                                                            | Used for                              |
|---------------------------------------------------------------------------------|---------------------------------------|
| `cross_trial_analysis_egk_april30_meta_9trials.csv`                              | template ground truth                 |
| `harmonization_outputs/harmonized_11trials.csv`                                  | pipeline final output                 |
| `harmonization_outputs/harmonized_9trials_reproduced.csv`                        | pipeline 9-trial reproduction         |
| `harmonization_outputs/validation_report.csv`                                    | cell-level mismatches                 |
| `harmonization_outputs/validation_summary.csv`                                   | (trial, column) match rates           |
| `harmonization_outputs/flagged_for_review.csv`                                   | NA-and-flagged rows + reasons         |
| `harmonization_outputs/source_evidence_report.csv`                               | per-(trial, field) source provenance  |
| `harmonization_outputs/provenance_long.csv`                                      | per-cell extraction trail             |
| `harmonization_outputs/final_handoff_report.md`                                  | prior decision context                |
| `harmonization_outputs/nonperfect_match_review.md`                               | severity classifications              |
| `harmonization_outputs/bor_binary_review_candidates.csv` / `.md`                 | prior 10026 BOR.binary investigation  |
| `10026-clinical/response_04282024.csv`                                           | 10026 source `D3_Alt_1`               |
| `10026-clinical/Data_Dictionary.xlsx`                                            | 10026 codebook (CRm/CRi definitions)  |
| `10013-clinical/*` (28 CSVs + CIDC_Annotation*.xlsx + DataDictionary*.xlsx)      | Cimac.id absence verification          |
| `14C0059G-clinical/*` (26 CSVs + field_locations.docx)                           | Cimac.id absence verification          |
| `S1400I-clinical/Clinical Dataset 2023_03_14.csv`                                | S1400I `age_num`                       |
| `S1400I-clinical/Clinical data dictionary.docx`                                  | S1400I `age_num` definition            |
| `S1400I-clinical/CIDC_Annotations_S1400I_20230323.xlsx`                          | S1400I truncation note                 |
| `10021-clinical/10021_Variable_Definitions.docx`                                 | searched for bor_bin/pfs_bin (not found) |
| `EAY131-Z1D-clinical/DataDictionary_*.xlsx`                                      | searched for bor_bin/pfs_bin (only `pfs_status` defined) |
| `GU16-257-clinical/data_dictionary.2023-01-19.xlsx`                              | searched for bor_bin/pfs_bin (not found) |

---

## 9. Out-of-scope notes

- The other sub-1.000 cells (10104 os_time/os_stat/BOR.binary/pfs_time;
  ABTC1603 pfs_stat; CIMAC-e4412 BOR/os_time/pfs_time/BOR.binary; GU16-257
  pfs_time; CIMAC-9204 race/age/Collection_Event_alt; 10026 treatment;
  ABTC1603 treatment) are not covered here. See `final_handoff_report.md`
  §6 and `nonperfect_match_review.md`.
- No code, config, or harmonized CSV has been modified by this report.
- The two files produced by this investigation are:
  - `harmonization_outputs/source_evidence_discrepancy_report.md` (this file)
  - `harmonization_outputs/source_evidence_discrepancy_report.csv` (machine-readable rows)
