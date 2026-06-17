# BOR.binary review candidates

Read-only investigation of the ~80 BOR.binary non-matching cases. Each
group below is a *reviewable unit* (one row in
`bor_binary_review_candidates.csv`), not necessarily one data row.

No pipeline code or config has been changed. This document is for
review planning only.

## Scope of the problem

Total BOR.binary mismatches across the 9 template trials: **79**. They
split across three trials:

| Trial         | Mismatches | Validation match rate |
|---------------|-----------:|----------------------:|
| 10026         | 54         | 0.748                 |
| 10104         | 17         | 0.920                 |
| CIMAC-e4412   | 8          | 0.952                 |

The remaining 6 template trials (10021, 9204, ABTC1603, gu16257,
s1400i, EAY131-Z1D) are at **1.000** for BOR.binary. The two new
trials with no template (10013, 14C0059G) are reviewed below.

## How BOR.binary is currently produced (per trial)

| Trial         | Extraction method            | Source field                                        | Confidence | Notes                                                                                                  |
|---------------|------------------------------|-----------------------------------------------------|-----------:|--------------------------------------------------------------------------------------------------------|
| 10026         | derived_bor_binary           | `response_04282024.csv :: D3_Alt_1`                 | 0.95       | 54 rows fall through because source codes (`CRm`, `CRi`, `-`, NaN) are not in the global map.          |
| 10104         | derived_bor_binary           | `10104_arm*_response*.csv :: best_response`         | 0.95       | 17 mismatches: 9 are template anomalies / convention differences; 8 are source-NaN/template-`other`.   |
| 10021         | derived_bor_binary           | `AllPatientData* :: RECIST clinical benefit status` | 0.95       | Template uses pre-binarized "Clin-Ben"/"No C-B"; mapping verified (P1#4).                              |
| 9204          | derived_bor_binary           | `best_response.{ipi,nivo}*.csv :: best_response`    | 0.95       | Long-form codes ("Morphological Complete Remission" etc.) mapped per P3 pass.                          |
| ABTC1603      | trial_constant               | (none)                                              | 0.95       | Committed assumption: template is constant `other` for all 148 rows (P1#3).                            |
| GU16-257      | derived_bor_binary           | `response*.csv :: CLCRFL` (Y/N/NE)                  | 0.95       | Y→R, N→NR, NE→other (P1#7/P1#8).                                                                       |
| S1400I        | derived_bor_binary           | best_response source columns                        | 0.95       | All 561 rows match template.                                                                           |
| EAY131-Z1D    | derived_bor_binary           | best_response source columns                        | 0.95       | All 63 rows match template.                                                                            |
| CIMAC-e4412   | derived_bor_binary           | `baseline_outcomes.xlsx :: BEST_OVERALL_RESP_CONF`  | 0.95       | 8 rows fall through because source label is `Unevaluable [<reason>]` (bracketed variants).             |
| 10013         | derived_bor_binary_no_BOR    | `response_updated_2024-11-07.csv :: D1`             | 0.00       | No CIDC BOR code in source; all 196 rows NA + flagged.                                                 |
| 14C0059G      | derived_bor_binary           | `response_off_treatment_date_of_death.csv :: Best Response to Treatment_Short Value` | 0.95 | Source uses standard CIDC short codes (SD, PD); 22/23 rows mapped, 1 NA. |

**Current global rule** (`scripts/config/harmonization_config.yaml`
under `value_normalizations.BOR.binary`):

```
R    ← CR, PR, Complete Response, Partial Response, UPR, Unconfirmed Partial Response,
        Clin-Ben, Clinical Benefit, Y, Morphological Complete Remission, Partial Remission
SD   ← SD, Stable Disease, STA, Stable
NR   ← PD, Progressive Disease, Progressive Disease or Relapsed Disease,
        SYMP, Symptomatic Deterioration, INC, Inconclusive,
        NASS, Not Assessable, No C-B, No Clinical Benefit, N,
        Persistent Disease, Progression
other ← UE, Unevaluable, NE, Not Applicable
CRm  ← "CR with MRD-"
CRi  ← "CR with incomplete count recovery"
```

## 1. BOR.binary confidence per trial

Confidence is recorded in `provenance_long.csv` as the `confidence`
column. For BOR.binary specifically:

- **Template trials at 1.000 match** (10021, 9204, ABTC1603, gu16257,
  s1400i, EAY131-Z1D): all rows at `confidence = 0.95` and the
  extraction method is one of `derived_bor_binary` or
  `trial_constant`. Evidence is provided by both the template
  cross-tab match and a committed YAML rule.

- **Template trials with mismatches** (10026, 10104, CIMAC-e4412):
  the *successfully mapped* rows are still at confidence 0.95; the
  unmapped rows are at confidence 0.00 (extraction_method =
  `derived_bor_binary_no_BOR`) and appear in
  `flagged_for_review.csv` per the no-silent-guessing policy. So the
  pipeline is internally consistent — it does not overstate
  confidence on the rows where it disagrees with the template.

- **New trials without template** (10013, 14C0059G): confidence should
  be interpreted as follows:
  1. **Source-label match to a documented CIDC short code** (CR / PR /
     SD / PD / NE / UE) → high confidence (≥0.95). This is the case
     for 14C0059G's 22 mapped rows.
  2. **Source-label match to a documented long-form description in
     the YAML** (e.g., "Stable Disease") → high confidence.
  3. **Source-label is a free-text or trial-specific code not in any
     map** (e.g., 10013's "Protocol-defined pCR (…)") → 0.0
     confidence, NA emitted, and the row is flagged. A clinical
     reviewer must confirm the intended mapping before the pipeline
     commits a rule.
  4. **No BOR source field at all** → 0.0 confidence,
     `derived_bor_binary_no_BOR`, NA + flagged. The new-trial
     extractor needs to be pointed at a different source column.

## 2. R-vs-NR non-matches (9 rows across 2 trials)

The cases where the pipeline emits R but template has NR (or vice
versa) all sit in 10104. Each case is enumerated below by the source
BOR value the pipeline saw via provenance, then the template's
BOR.binary, the pipeline's emitted BOR.binary, and the likely cause.

| Group | Source BOR | Template BOR.binary | Pipeline BOR.binary | Rows | Likely cause                                                                 |
|-------|-----------:|--------------------:|--------------------:|-----:|------------------------------------------------------------------------------|
| R005  | CR         | NR                  | R                   | 2    | Template anomaly — CR cannot clinically be NR.                               |
| R006  | PD         | R                   | NR                  | 2    | Template anomaly — PD cannot clinically be R.                                |
| R007  | PD         | SD                  | NR                  | 3    | Template anomaly — PD vs SD is a clear clinical distinction.                 |
| R008  | SD         | R                   | SD                  | 2    | Convention difference — template lumps SD into R; pipeline keeps SD bucket.  |

**Recommendation:** for R005–R007 (7 rows), accept the pipeline output
as canonical and record these rows under `template_anomalies.csv` (the
mechanism already used for the EAY131-Z1D `sex_in_arm_leak` anomaly).
For R008 (2 rows), this is a convention decision; the current pipeline
behaviour (SD as its own bucket) follows CIDC standards and the rest of
the cross-trial data, so no change is recommended.

## 3. "other" category investigation

### Current state of `other`

`other` appears in the final harmonized output for **161 rows** across
4 trials (out of 2,000 total). Every appearance has source support:

| Trial          | Rows of `other` | Source basis                                                 |
|----------------|----------------:|--------------------------------------------------------------|
| ABTC1603       | 148             | Trial constant; template is constant `other` (committed).    |
| CIMAC-gu16257  | 6               | Source `CLCRFL` = `NE` (Not Evaluable).                      |
| EAY131-Z1D     | 6               | Source = `UE` (Unevaluable).                                 |
| CIMAC-9204     | 1               | Source = `Not Applicable`.                                   |

None of these is a candidate for re-mapping. All are correctly
classified as `other`.

### Cases that the template labels `other` but the pipeline emits NA

| Trial        | Source BOR                    | Rows | Recommendation                                                |
|--------------|-------------------------------|-----:|---------------------------------------------------------------|
| 10026        | NaN (blank)                   | 16   | **Preserve NA.** Template invents `other` without source.     |
| 10104        | NaN (blank)                   | 8    | **Preserve NA.** Same pattern as above.                       |
| CIMAC-e4412  | `Unevaluable [<reason>]`      | 8    | **Safe re-map to `other`.** Source label clearly indicates unevaluable; template confirms.  |

**Conservative ruling:** of these 32 rows currently NA, only the 8
CIMAC-e4412 "Unevaluable […]" rows have a source label that
unambiguously supports `other`. The 24 source-NaN rows should remain
NA — the template's choice of `other` for blank source data is not a
mapping we want to silently replicate.

### Should `other` remain distinct from blank/NA?

Yes. The two carry different information:

- **`other`** = source explicitly labelled the response as non-RECIST
  (Not Evaluable / Unevaluable / Not Applicable).
- **NA / blank** = source has no response value at all (data missing).

Conflating them would silently drop the distinction between
"unevaluable" and "missing", which downstream analyses commonly need
to separate.

## 4. Review-candidate groups (also in `bor_binary_review_candidates.csv`)

13 review groups, covering all 79 template mismatches plus the
new-trial situations. Priorities use the same P1/P2/P3 scheme as
`review_priority_checklist.csv`.

### R001 — 10026 `CRm` source code → reproduced NA *(P2, 25 rows)*
- **Issue type:** mapped_to_other (currently NA)
- **Source:** `response_04282024.csv :: D3_Alt_1` value `"CRm"`
- **Cause:** YAML `BOR.binary.CRm` only matches the long form `"CR
  with MRD-"`. The literal short code `CRm` used by 10026 source and
  by the template is not in the map.
- **Decision:** add the short code to the CRm bucket.
- **Action:** add `"CRm"` to `BOR.binary.CRm` in
  `harmonization_config.yaml` value_normalizations (or add a
  10026-specific value_map). Low-risk; source label matches template
  label exactly.

### R002 — 10026 `CRi` source code → reproduced NA *(P2, 11 rows)*
- Same pattern as R001 for `CRi`.

### R003 — 10026 `"-"` source code → reproduced NA *(P3, 2 rows)*
- **Issue type:** source_ambiguity
- **Cause:** dash is undefined in the global map.
- **Decision:** does `"-"` mean unknown, not-yet-evaluated, or
  something else? Template carries the literal `"-"`.
- **Action:** very low-impact (2 rows). Recommend keeping NA unless a
  clinical reviewer explicitly confirms a category.

### R004 — 10026 source BOR NaN, template assigns `other` *(P3, 16 rows)*
- **Issue type:** missing_or_NA
- **Cause:** template invents `other` when source is blank.
- **Decision:** preserve pipeline NA.
- **Action:** no code change. Document as a known template convention
  divergence.

### R005 — 10104 CR source, template marks NR *(P2, 2 rows)*
- **Issue type:** R_vs_NR_mismatch (template anomaly)
- **Action:** keep pipeline `R`; record in template_anomalies.

### R006 — 10104 PD source, template marks R *(P2, 2 rows)*
- **Issue type:** R_vs_NR_mismatch (template anomaly)
- **Action:** keep pipeline `NR`; record in template_anomalies.

### R007 — 10104 PD source, template marks SD *(P2, 3 rows)*
- **Issue type:** R_vs_NR_mismatch (template anomaly)
- **Action:** keep pipeline `NR`; record in template_anomalies.

### R008 — 10104 SD source, template marks R *(P3, 2 rows)*
- **Issue type:** source_ambiguity (convention difference)
- **Action:** keep SD bucket; document the convention difference.

### R009 — 10104 source BOR NaN, template assigns `other` *(P3, 8 rows)*
- Same as R004.

### R010 — CIMAC-e4412 `Unevaluable [<reason>]` → reproduced NA *(P2, 8 rows)*
- **Issue type:** mapped_to_other
- **Cause:** YAML expects literal `"Unevaluable"`; source has bracketed
  variants like `"Unevaluable [Scan obtained <6wks(criteria for SD)]"`.
- **Decision:** add a contains-rule.
- **Action:** add a `contains: "Unevaluable"` rule to BOR.binary
  (and BOR) value_normalizations with confidence 0.95. Evidence
  strong: source label is unambiguous and template confirms `other`.

### R011 — 10013 long-form pCR description → reproduced NA *(P2, 196 rows)*
- **Issue type:** new_trial_no_template
- **Cause:** source `D1` contains a long English sentence describing
  protocol-defined pCR; no rule matches.
- **Decision:** **needs clinical reviewer input.** Confirm whether
  `"Protocol-defined pCR (…)"` should map to BOR=CR / BOR.binary=R,
  and how non-pCR cases are encoded (if at all) in the source.
- **Action:** after clinical confirmation, add a value_map (or
  contains-rule for `"Protocol-defined pCR"`) and rerun.

### R012 — 14C0059G SD/PD short codes → BOR.binary SD/NR *(P3, 23 rows)*
- **Issue type:** new_trial_no_template
- **Cause:** none — this is the expected behaviour. Source uses CIDC
  short codes (SD, PD); pipeline applies the global map.
- **Decision:** confirm acceptance; document in handoff for the
  new-trial review pass.
- **Action:** no change required.

### R013 — ABTC1603 trial_constant `other` *(P3, 148 rows)*
- **Issue type:** mapped_to_other (already committed)
- Not a defect; listed for completeness.
- **Action:** none.

## 5. Summary recommendation

- **13 review groups identified, covering 79 template mismatches plus
  219 new-trial rows (196 in 10013 + 23 in 14C0059G) plus 148 already-
  committed ABTC1603 rows.**

- **Safe to fix later via config-only changes (low risk, strong
  evidence):**
  - R001 — 10026 `CRm` short-code mapping (25 rows)
  - R002 — 10026 `CRi` short-code mapping (11 rows)
  - R010 — CIMAC-e4412 `Unevaluable […]` contains-rule (8 rows)

  Combined impact: **44 rows would be filled in correctly** by config
  edits with template-confirmed evidence. These should be the first
  three approved decisions.

- **Should be documented as template anomalies (no code change), not
  chased:**
  - R005, R006, R007 — 10104 template anomalies (7 rows total)
  - R008 — 10104 SD-lumping convention difference (2 rows)
  - R004, R009 — source-NaN-vs-template-`other` (24 rows total)

  Total: **33 rows** where preserving pipeline output is the
  source-supported choice. These should be added to
  `template_anomalies.csv` for traceability.

- **Requires human clinical judgment before any rule is committed:**
  - R003 — 10026 `"-"` interpretation (2 rows; low impact, can wait).
  - R011 — 10013 protocol-defined pCR text → BOR (196 rows; **high
    impact, P2**). This is the single largest BOR.binary gap in the
    current dataset.

- **Acceptable as-is (no action):**
  - R012 — 14C0059G new-trial mapping (22 mapped + 1 NA).
  - R013 — ABTC1603 trial-constant `other` (148 rows; already
    committed).

- **Confidence for new trials** should be assessed from the *extraction
  method* and *source-label provenance*, not from a template
  comparison (which is unavailable). Use:
  1. Is the source label a documented CIDC code in the global map?
     → high confidence.
  2. Does the source label match a trial-specific committed value_map
     with documented evidence in the handoff §4 table? → high
     confidence.
  3. Is the source label free-text or unmapped? → 0.0 confidence;
     pipeline correctly emits NA + flag; reviewer must confirm a rule
     before the pipeline can commit it.

- **`other` should remain a distinct category from blank/NA**, because
  the two carry different downstream meaning (explicitly unevaluable
  vs missing). Conflating them is not recommended.

No pipeline code or config has been changed by this investigation.
The two artefacts produced are:

- `bor_binary_review_candidates.csv`
- `bor_binary_review_candidates.md` (this file)
