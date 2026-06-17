# Expanded reviewer examples — CIMAC harmonization

Draft generated 2026-05-20 from the current repository state.
Scope: 11 trials (BACCI excluded). `exclusion_and_order_checks.txt` → `VERDICT: PASS`.
Source artifacts: `validation_summary.csv`, `validation_report.csv`, `flagged_for_review.csv`,
`provenance_long.csv`, `top_review_items_with_source_evidence.{md,csv}`, `final_handoff_report.md`,
and the raw `*-clinical/` files cited inline. No code, config, harmonized CSVs, or pipeline outputs
were modified to produce this draft.

Discrepancy types are ordered by **number of affected entries (cells), largest first.**
"Confirmation" items at the top are already-implemented high-impact rules, not unresolved discrepancies.

---

## 1. 120-day landmark rule for `pfs_bin` (already implemented; reviewer confirmation only)
**Affected entries:** 2,000 derived cells (every row in `harmonized_11trials.csv`)
**Priority:** confirmation
**Status:** implemented pending confirmation
**Reviewer-confirmation item — not an unresolved discrepancy.**

### Why this matters
The 120-day landmark is the rule that reproduces Edgar's `pfs_bin` column at 100% on every applicable
template trial. Match rate climbed from ~9% to ~99% after rollout (`derived_120d_rules_change_log.md`
narrative inside `final_handoff_report.md` §4 and `top_review_items_with_source_evidence.md`).
Because no SAP or codebook in this repo defines it, the rule is marked "template-supported derived
rule; pending final clinical confirmation".

### Representative example
- trial: 10104
- field(s): pfs_bin
- cimac_part_id: CWWG7K5
- Cimac.id: CWWG7K5JD.01
- Collection_Event: Baseline
- Edgar/template value: (same as pipeline for this matched row)
- pipeline value: 1 (or 0/NaN depending on pfs_time + pfs_stat)
- source file path: derived in pipeline from `harmonized_11trials.csv` `pfs_time` and `pfs_stat`
- source column/field: `pfs_time, pfs_stat`
- source value or short quote (from `provenance_long.csv`):
  `pfs_time>=120.0 → pfs_bin=1 (120-day landmark; template-supported, pending clinical confirmation)`

### Interpretation
Rule: `pfs_bin = 1 iff pfs_time >= 120`; `0 iff pfs_time < 120 AND pfs_stat == 1`;
`NaN iff pfs_time < 120 AND pfs_stat == 0`. All 2,000 rows in
`harmonized_11trials.csv` carry `extraction_method = derived_pfs_bin_120d` in
`provenance_long.csv`.

### Reviewer question
Do you confirm the 120-day `pfs_bin` landmark rule as the official derivation, allowing the
"pending final clinical confirmation" note to be removed?

### If approved, tell Claude
No code change required. Update the provenance `notes` template in `scripts/extractors/_helpers.py`
(or wherever `derived_pfs_bin_120d` notes are constructed) to drop the
"pending final clinical confirmation" suffix and add a citation to the SAP/codebook section the
reviewer points to. Document the confirmation in `final_handoff_report.md` § 4.

---

## 2. 120-day landmark rule for `bor_bin` (already implemented; reviewer confirmation only)
**Affected entries:** 2,000 derived cells
**Priority:** confirmation
**Status:** implemented pending confirmation
**Reviewer-confirmation item — not an unresolved discrepancy.**

### Why this matters
Same situation as item 1. `bor_bin` match rate climbed from ~30% to ~99% (8 of 9 trials at 1.000)
after the SD-landmark rule rolled out.

### Representative example
- trial: 10026
- field(s): bor_bin
- cimac_part_id: CBUPOJV
- Cimac.id: CBUPOJV2D.01
- Collection_Event: End_of_Treatment
- Edgar/template value: NaN
- pipeline value: 1
- source file path: derived from `BOR.binary` (= R) and `pfs_time`
- source column/field: `BOR.binary, pfs_time`
- source value or short quote (provenance):
  `BOR.binary='R' -> bor_bin=1 (120-day rule) | template-supported derived rule, pending final clinical confirmation`

### Interpretation
Rule: `bor_bin = 1 iff BOR.binary == 'R' OR (BOR.binary == 'SD' AND pfs_time >= 120)`;
`0 iff 'NR' OR ('SD' AND pfs_time < 120)`; `NaN` otherwise. All 2,000 rows carry
`extraction_method = derived_bor_bin_120d`.

### Reviewer question
Do you confirm the 120-day `bor_bin` SD-landmark rule as the official derivation?

### If approved, tell Claude
No code change required. Drop the "pending final clinical confirmation" suffix in the
provenance notes; add the citation source the reviewer supplies; update
`final_handoff_report.md` § 4.

---

## 3. 10013 bulk new-trial gaps — survival, arm, phase, CE-alt missing in source
**Affected entries:** ~1,960 cells (196 participant-rows × 10 fields with `value_NA_at_extraction`)
**Priority:** P1
**Status:** missing source files

### Why this matters
10013 has no template and no source files for survival or arm assignment, so 10 of the 19
harmonized columns are NA for every 10013 row. This is by far the largest unresolved gap by cell
count.

### Representative example
- trial: 10013
- field(s): arm, phase, os_time, os_stat, pfs_time, pfs_stat, BOR.binary, bor_bin, pfs_bin, Collection_Event_alt
- cimac_part_id: CHCO0M4
- Cimac.id: (NaN — see item 5)
- Collection_Event: Baseline
- Edgar/template value: (no template — 10013 is a new trial)
- pipeline value: NaN for all listed fields
- source file path checked: `10013-clinical/response_2023-09-13.csv`, `10013-clinical/response_updated_2024-11-07.csv`, `10013-clinical/specimen_collection_2023-09-13.csv`, `10013-clinical/treatment_2023-09-13.csv`
- source column/field: (no survival, arm, phase, or CE-alt columns present)
- source value or short quote (flagged_for_review.csv):
  `10013 os_time not derivable from response file — flag`;
  `10013 arm not derivable from source — flag`;
  `raw_ce='Baseline': no mapping configured for 10013 (flag)`

### Interpretation
The CIDC team did not deliver per-patient survival or arm assignment CRFs for 10013, and the
`Collection_Event` strings in `specimen_collection_2023-09-13.csv` ("Baseline",
"Definitive Surgery", "Post Cycle 1") have no harmonized analogue in the YAML.

### Reviewer question
Can the protocol team supply survival CRFs (OS/PFS times + events), arm assignment, and a
preferred `Collection_Event_alt` mapping for 10013? Otherwise these 10 fields remain NA.

### If approved, tell Claude
After receiving the new files, add their paths to `scripts/config/harmonization_config.yaml`
under `10013-clinical.sources`, wire them up in `scripts/extractors/nci_10013.py` with
explicit anchor columns, and add `10013-clinical.collection_event_alt_map` entries
(e.g. `Baseline: Baseline`, `Post Cycle 1: C2`, `Definitive Surgery: Surgery`) confirmed with
the reviewer. Then rerun `./scripts/run_full_harmonization.sh`.

---

## 4. S1400I age — decimal precision lost upstream
**Affected entries:** 561 cells (every S1400I row; match_rate 0.0)
**Priority:** P1
**Status:** missing source file

### Why this matters
The template's `age` is a decimal (per-sample age at collection, e.g. 50.5, 47.9, 83.8). The source
file's `age_num` is integer (age at enrollment). The pipeline emits the integer and flags every row.
This single discrepancy accounts for the largest mismatch group in `validation_report.csv`.

### Representative example
- trial: CIMAC-s1400i
- field(s): age
- cimac_part_id: CCZRBHF
- Cimac.id: CCZRBHF6N.01
- Collection_Event: Baseline
- Edgar/template value: 50.5
- pipeline value: NaN (flagged; proposed mapping was 50.0)
- source file path: `S1400I-clinical/Clinical Dataset 2023_03_14.csv`
- source column/field: `age_num`
- source value or short quote:
  `age_num=50` (integer);
  `S1400I-clinical/CIDC_Annotations_S1400I_20230323.xlsx` Sheet1 row 3: "age_num | Age truncated | Age truncated to remove identifying specificity"

### Interpretation
SWOG truncated decimal age before delivery to remove identifying specificity. Per-sample
collection dates that would let the pipeline reconstruct `age_at_collection` are not in the
source bundle either.

### Reviewer question
Can SWOG supply per-patient un-truncated decimal age (or per-sample collection-date file)?
If not, do we substitute `age_num` (integer enrollment age) into the harmonized `age` column,
or leave all 561 rows as NA?

### If approved, tell Claude
**If SWOG supplies the decimals:** add the new file to
`S1400I-clinical.sources.age_decimal` in YAML and update `scripts/extractors/s1400i.py` to
read the new column with `extraction_method=age_at_collection`.
**If substituting `age_num`:** raise the s1400i age threshold below 0.55 in
`harmonization_config.yaml` for the `age` field, or change `extraction_method=age_at_enrollment`
to confidence 0.85 with a YAML note. Then rerun the pipeline.

---

## 5. 10013 and 14C0059G missing `Cimac.id` (no sample manifest)
**Affected entries:** 219 cells (10013: 196, 14C0059G: 23)
**Priority:** P1
**Status:** missing source file

### Why this matters
The harmonized table's primary key includes `Cimac.id`; without it, sample-level joins against
CIDC sample manifests, assay tables, or downstream analyses cannot be performed for these two
trials.

### Representative examples
- trial: 10013
- field(s): Cimac.id
- cimac_part_id: CHCO0M4
- Collection_Event: Baseline
- Edgar/template value: (no template — new trial)
- pipeline value: NaN
- source file path checked: `10013-clinical/specimen_collection_2023-09-13.csv`, `10013-clinical/CIDC_Annotation_2024-11-08.xlsx`, and every other 10013 file
- source column/field: (no sample-level Cimac.id column anywhere)
- source value or short quote (flagged_for_review.csv):
  `10013 source files do not contain sample-level Cimac.id; external CIMAC manifest required`

For 14C0059G, the same situation applies to all 23 rows. The single most likely candidate file
checked was `14C0059G-clinical/research_sample_collection_apheresis.csv` (no sample-id column).

### Interpretation
The CIMAC `Cimac.id` strings (`{patient_id}{2-char}.01` form) are populated by the CIDC
infrastructure team from sample manifests after specimen receipt. Brute-force pattern scans
of every cell in every file in both trial directories returned zero matches.

### Reviewer question
Can the CIDC team supply external sample manifests for 10013 and 14C0059G with columns
`cimac_part_id`, `Cimac.id`, `Collection_Event`? Without them, these 219 rows must remain NA.

### If approved, tell Claude
Drop the new manifest CSVs into the respective trial directories, register them under
`<trial>-clinical.sources.cimac_manifest` in YAML, and update
`scripts/extractors/nci_10013.py` and `scripts/extractors/nih_14c0059g.py` to read `Cimac.id`
from those manifests with `extraction_method=cimac_manifest_lookup` (confidence 1.0). Rerun
the pipeline; expect 219 flagged rows to drop.

---

## 6. 10013 protocol-defined pCR free-text → `BOR` / `BOR.binary`
**Affected entries:** 67 source rows in `response_updated_2024-11-07.csv` (pipeline emits NaN for the
corresponding 196 harmonized `BOR.binary` cells today)
**Priority:** P1
**Status:** unresolved (contains-rule candidate)

### Why this matters
10013's response file describes the BOR endpoint as one long English sentence in the `D1` column.
The pipeline has no contains-rule for it, so `BOR` and `BOR.binary` are NA for every 10013 row.

### Representative example
- trial: 10013
- field(s): BOR, BOR.binary
- cimac_part_id: CHCO0M4
- Cimac.id: (NaN — see item 5)
- Collection_Event: Baseline
- Edgar/template value: (no template)
- pipeline value: NaN
- source file path: `10013-clinical/response_updated_2024-11-07.csv` (read with `skiprows=1`)
- source column/field: `D1` (BOR text); `D13` (pCR Yes/No: 28 Yes / 33 No / 6 NE)
- source value or short quote:
  `D1` cell: "Protocol-defined pCR (no histology evidence of invasive tumor cells in the surgical breast specimen and sentinel or axillary lymph nodes)" (identical for all 67 rows)
  `D3` distribution: CR 24, PR 22, SD 10, MR 2, NaN 6
  `D13` distribution: Yes 28, No 33, NE 6

### Interpretation
The text in `D1` defines the BOR endpoint. The actual per-patient response is in `D3`
(RECIST-like CR/PR/SD/MR) or `D13` (pCR Yes/No/NE). A contains rule on `D1` plus a value-map on
`D3` or `D13` would populate both fields.

### Reviewer question
(a) Should the `D1` text be matched via contains-rule to `BOR.binary = R` (since pCR is a
complete response)?
(b) Or should `D3` (CR/PR/SD/MR) drive `BOR` and `BOR.binary`, with `D13` used as a tie-breaker?
(c) What should MR (minor response, n=2) map to?

### If approved, tell Claude
Approved option (b) is most likely:
- Register `response_updated_2024-11-07.csv` under `10013-clinical.sources.response`.
- In `scripts/extractors/nci_10013.py`, read `D3` for `BOR` and `D13` for `pCR`.
- In `harmonization_config.yaml` under `value_normalizations.BOR.binary`, add `10013` trial overrides:
  `R: [CR, "Yes"]`, `NR: [PD]`, `SD: [SD]`, `other: [MR, NE]`.
- Cite the `D1` text in the per-cell `notes` for traceability.
Rerun the pipeline.

---

## 7. 10104 OS/PFS anchor mismatch — template uses `tx_phase_end_dt` for crossover / off-treatment
**Affected entries:** 68 cells (40 `os_time` + 14 `pfs_time` + 7 `pfs_bin` + 7 `bor_bin`)
**Priority:** P2
**Status:** pipeline rule refinement

### Why this matters
For 40 of 40 mismatched `os_time` rows, the pipeline value exceeds the template value
(mean delta = +332 days, range +70 to +953). This systematic, one-direction drift cascades into
`pfs_bin` and `bor_bin` (which depend on the 120-day landmark of `pfs_time`).

### Representative example
- trial: 10104
- field(s): os_time, pfs_time, pfs_bin, bor_bin
- cimac_part_id: CWWG289
- Cimac.id: CWWG289LX.01
- Collection_Event: Cycle2_Day1
- Edgar/template value: os_time=84 ; pfs_time=547 ; pfs_bin=1 ; bor_bin=1
- pipeline value:    os_time=1037 ; pfs_time=56  ; pfs_bin=0 ; bor_bin=0
- source file path: `10104-clinical/10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv` (read with `skiprows=1`)
- source column/field: pipeline uses `overall survival time in days from first_cycle_first_day to DEATH_DT or last_follow_up_date` (=1037) and `progression free survival time in days from first_cycle_first_day to progression_date or DEATH_DT or last_follow_up_date` (=56). Template appears to use `Days from first_cycle_first_day to tx_phase_end_dt` (=84) for this patient.
- source value or short quote: for CWWG289 the source row contains `tx_phase_end_dt=91`, `last_follow_up_date=1044`, `progression_date=63`, `DEATH_DT=NaN`, `PT_OFF_TX_OFF_ST_RSN_CD='Disease progression on study'`, `best_response='PD'`.

### Interpretation
For patients who go off-treatment for disease progression (or who cross over to a different arm),
Edgar's `os_time` follows the patient only up to `tx_phase_end_dt`, not all the way to
`last_follow_up_date`. The pipeline's current rule is a single uniform anchor.

### Reviewer question
Should the 10104 extractor switch to a conditional anchor: use
`Days from first_cycle_first_day to tx_phase_end_dt` when `PT_OFF_TX_OFF_ST_RSN_CD` is non-null
(or `Date_of_treatment Cross Over from Arm B to Arm C` is non-null), and otherwise the survival
column? Re-classify `os_stat=0` for those patients (censored at off-tx)?

### If approved, tell Claude
In `scripts/extractors/nci_10104.py`, branch the `os_time` and `pfs_time` extraction:
- If `Date_of_treatment Cross Over from Arm B to Arm C` is non-null OR `PT_OFF_TX_OFF_ST_RSN_CD` is non-null AND `DEATH_DT` is null: use `Days from first_cycle_first_day to tx_phase_end_dt`; set `os_stat=0` (censored).
- Else use the existing survival column.
- Use `extraction_method=os_time_anchor_off_tx` / `pfs_time_anchor_off_tx` for the new branch and cite the rule in the `notes`. Rerun pipeline; expected drop of ~68 cell mismatches and corresponding flagged-row reduction in `pfs_bin`/`bor_bin`.

---

## 8. 10104 BOR / BOR.binary / os_stat template anomalies (R005–R009 family)
**Affected entries:** 43 cells (9 `BOR` + 17 `BOR.binary` + 17 `os_stat`)
**Priority:** P2 / P3
**Status:** likely template anomaly

### Why this matters
For 8 of the 17 `BOR.binary` rows the template literally contains the string `"other"` even though
the source `best_response` is NA or unambiguous. For 9 `BOR` rows, the template carries `PR` but
the source `best_response` is `PD`. These look like prior-template artifacts; the pipeline
faithfully reproduces source so it does not introduce these strings.

### Representative example
- trial: 10104
- field(s): BOR, BOR.binary
- cimac_part_id: CWWG289
- Cimac.id: CWWG289LX.01
- Collection_Event: Cycle2_Day1
- Edgar/template value: BOR=PR ; BOR.binary=R
- pipeline value: BOR=PD ; BOR.binary=NR
- source file path: `10104-clinical/10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv`
- source column/field: `best_response`
- source value or short quote: `best_response='PD'` for CWWG289 (template `BOR=PR` contradicts the source)

A second flavor: 8 rows where template `BOR.binary='other'` but source `BOR` is NA (e.g. CWWGCSR
Baseline, CWWGCA9 Baseline, CWWGS8N Baseline). Pipeline correctly returns NaN.

### Interpretation
Either the template was hand-edited at the time of generation, or it was built from a different
snapshot of the source file. The current source clearly does not support those values. These look
like the R005–R009 anomaly family already partially captured in
`harmonization_outputs/template_anomalies.csv`.

### Reviewer question
Confirm that R005–R009 + the `"other"`/`"PR"`/`"SD"` template values for the 43 cells listed in
`validation_report.csv` for 10104 are template anomalies, and that the pipeline should keep
emitting source-faithful values?

### If approved, tell Claude
For each of the 43 mismatched (cimac_part_id, Cimac.id, Collection_Event, column) tuples, add an
entry to `harmonization_outputs/template_anomalies.csv` via the
`scripts/generate_review_report.py` template-anomaly generator (extend the per-trial
"template anomaly patterns" list in that script). No change to harmonized values. Document the
decision in `final_handoff_report.md` § Template anomalies.

---

## 9. 10026 CRm / CRi → R (D3a) vs template preserving short codes
**Affected entries:** 36 cells (`BOR.binary`: CRm=25, CRi=11)
**Priority:** P2
**Status:** implemented pending confirmation (D3a in effect)

### Why this matters
D3a maps CRm/CRi to `R` based on the 10026 Data Dictionary. The template instead preserved the
short codes verbatim. Closing this gap traded a 36-row `BOR.binary` improvement for a 54-row
`bor_bin` improvement (currently `bor_bin` is correct, `BOR.binary` mismatches remain).

### Representative example
- trial: 10026
- field(s): BOR.binary
- cimac_part_id: CBUPOJV
- Cimac.id: CBUPOJV2D.01
- Collection_Event: End_of_Treatment
- Edgar/template value: CRm
- pipeline value: R
- source file path: `10026-clinical/response_04282024.csv` (read with `skiprows=1`)
- source column/field: `D3_Alt_1`
- source value or short quote: `D3_Alt_1='CRm'`
- supporting data dictionary: `10026-clinical/Data_Dictionary.xlsx` Sheet1 row 95 — "CRm | Bone Marrow CR"; row 94 — "CRi | Morphologic Complete Remission with Incomplete Blood Count Recovery"; row 93 — "CR | Morphologic Complete Remission"

### Interpretation
Clinically, CRm and CRi are both complete-response variants and belong under `R`. Edgar's template
preserved the literal short codes, which is byte-fidelity but not semantically consistent with the
rest of the harmonized column.

### Reviewer question
Keep the D3a R-mapping (preferred — closes the `bor_bin` gap; 36 rows go into
`template_anomalies.csv`) **or** revert and pass CRm/CRi through verbatim (giving up the 36-row
`bor_bin` improvement)?

### If approved, tell Claude
**Default (keep R-mapping):** add the 36 mismatched rows to `template_anomalies.csv` via the
generator in `scripts/generate_review_report.py`. No harmonized-value change. Drop the
"pending final clinical confirmation" suffix from the `BOR.binary` notes.
**If reverting:** remove `CRm, CRi, "CR with MRD-", "CR with incomplete count recovery"` from
the global `value_normalizations.BOR.binary.R` list in `harmonization_config.yaml`. Rerun pipeline.

---

## 10. CIMAC-e4412 month→day rounding (`round()` vs `int()`)
**Affected entries:** 19 cells (11 `pfs_time` + 8 `os_time`)
**Priority:** P3
**Status:** source/pipeline rounding ambiguity

### Why this matters
The template's `os_time` and `pfs_time` values are off by exactly 1 day for these rows. The source
is in weeks; the pipeline multiplies by 30.4375 and applies `round()`, while the template
apparently applies `int()` truncation.

### Representative example
- trial: CIMAC-e4412
- field(s): os_time
- cimac_part_id: C29ZDAX
- Cimac.id: C29ZDAX0O
- Collection_Event: Baseline
- Edgar/template value: 90
- pipeline value: 91
- source file path: `E4412-clinical/baseline_outcomes.xlsx`
- source column/field: `os_wk`
- source value or short quote: `os_wk=2.97331` → `round(2.97331 × 30.4375)` = `round(90.51)` = 91. `int(90.51)` = 90.

A `pfs_time` example: C29ZE03 Baseline source `pfs_wk=0.70637` → pipeline 22, template 21.

### Interpretation
Edgar's template appears to truncate; the pipeline rounds. All 19 mismatches are exactly 1 day,
direction `pipeline = template + 1`.

### Reviewer question
Approve switching from `round()` to `int()` truncation for the e4412 month→day conversion?

### If approved, tell Claude
In `scripts/extractors/e4412.py`, change the unit-conversion call from
`round(months * 30.4375)` to `int(months * 30.4375)` for both `os_wk` and `pfs_wk`. Update the
provenance `notes` template (`time_unit_conv(×30.4375)`) to indicate truncation. Rerun pipeline.

---

## 11. 10026 `BOR.binary` template `"other"` / `"-"` with source-NA BOR
**Affected entries:** 18 cells (`"other"`: 16, `"-"`: 2)
**Priority:** P2 / P3
**Status:** likely template anomaly

### Why this matters
For 18 rows the template's `BOR.binary` carries `"other"` (16) or the literal string `"-"` (2)
but the underlying source `BOR` is NA. The pipeline correctly returns NaN.

### Representative example
- trial: 10026
- field(s): BOR.binary
- cimac_part_id: CBUPKKC
- Cimac.id: CBUPKKCIR.01
- Collection_Event: End_of_Lead_In
- Edgar/template value: `-`
- pipeline value: NaN
- source file path: `10026-clinical/response_04282024.csv`
- source column/field: `D3_Alt_1`
- source value or short quote: source `D3_Alt_1='-'` for CBUPKKC (this is the literal dash sentinel)
  Provenance note for the 16 `"other"` rows: `BOR is NA → BOR.binary NA`.

### Interpretation
The 16 `"other"` cells were probably hand-filled in the template when source BOR was NA; the 2
`"-"` cells reflect a sentinel dash value that the YAML does not have a mapping for. Both look
like template artifacts; pipeline behavior is correct.

### Reviewer question
Add these 18 rows to `template_anomalies.csv`? **Or** add `"-" → other` and `(BOR is NaN) → other`
rules to the YAML to bytewise-match the template?

### If approved, tell Claude
**Default (template anomaly):** add the 18 rows to `template_anomalies.csv` via the generator
in `scripts/generate_review_report.py`.
**If matching the template:** in `harmonization_config.yaml` add `"-": other` to
`value_normalizations.BOR.binary` (under 10026 trial overrides) and add a `derived_bor_binary_NA`
branch in `scripts/lib/extractor_base.py` that emits `"other"` when source BOR is NA for 10026.
Rerun pipeline.

---

## 12. CIMAC-e4412 "Unevaluable [<reason>]" → `other` (contains rule needed)
**Affected entries:** 16 cells (8 `BOR` + 8 `BOR.binary`)
**Priority:** P3
**Status:** source-codebook ambiguity (one-line YAML add)

### Why this matters
Source `BEST_OVERALL_RESP_CONF` contains bracketed variants ("Unevaluable [Scan obtained
<6wks(criteria for SD)]", "Unevaluable [Pt ended tx after C1]", "Unevaluable [No follow-up dx
assessment; patient death]", "Unevaluable [NPT before first dx assessment follow-up]",
"Unevaluable [pt went off tx after C1]"). The YAML expects the literal token `"Unevaluable"` and
therefore passes the bracketed strings through verbatim; the template normalized them to `other`.

### Representative example
- trial: CIMAC-e4412
- field(s): BOR
- cimac_part_id: C29Z0DA
- Cimac.id: C29Z0DAAF
- Collection_Event: Pre_D1_C2
- Edgar/template value: `other`
- pipeline value: `Unevaluable [Scan obtained <6wks(criteria for SD)]`
- source file path: `E4412-clinical/baseline_outcomes.xlsx`
- source column/field: `BEST_OVERALL_RESP_CONF`
- source value or short quote: `BEST_OVERALL_RESP_CONF='Unevaluable [Scan obtained <6wks(criteria for SD)]'`

### Interpretation
The template's normalization rule was "any Unevaluable [...] variant maps to other". A
contains-rule (rather than exact-match) on `Unevaluable` closes all 16 cells.

### Reviewer question
Approve adding a contains-rule `"Unevaluable" → other` to `value_normalizations.BOR` and
`value_normalizations.BOR.binary`?

### If approved, tell Claude
In `harmonization_config.yaml`, under `value_normalizations.BOR.other` and
`value_normalizations.BOR.binary.other`, add a new branch with `match_mode: contains` and the
token `"Unevaluable"`. If the current normalization helper does not support `contains`, add it
in `scripts/lib/normalize.py` (one-function change). Rerun pipeline.

---

## 13. ABTC1603 `pfs_stat` — death-without-progression not counted as event
**Affected entries:** 15 cells (`pfs_stat`: 15; cascades into 3 `pfs_bin`)
**Priority:** P2
**Status:** pipeline rule refinement

### Why this matters
The current pipeline rule is `pfs_stat = 1 iff Days to Progression non-null`. Standard oncology
convention counts death-from-any-cause without prior documented progression as a PFS event as well.
The template follows the standard convention; the pipeline misses 15 patients who died without
documented progression.

### Representative example
- trial: ABTC1603
- field(s): pfs_stat
- cimac_part_id: CG07P2D
- Cimac.id: CG07P2D11.01
- Collection_Event: Baseline
- Edgar/template value: 1
- pipeline value: 0
- source file path: `ABTC1603-clinical/abtc_1603_treatmentresponse_03042024_2024-04-17.csv` (skiprows=1)
- source column/field: `Vital Status`, `Days to Progression`, `Days to Death`, `Cause Death`
- source value or short quote: `Vital Status='DEAD'`, `Days to Progression=NaN`, `Days to Death=25`, `Cause Death='DUE TO OTHER CAUSE'`, `Comments='PULMONARY EMBOLISM'`

### Interpretation
6 of 41 patients in the file have `Vital Status='DEAD'` AND `Days to Progression=NaN`; these are
counted as `pfs_stat=1` by the template (and standard PFS convention) but as `pfs_stat=0` by the
current pipeline. The remaining 9 mismatches likely share the same pattern across timepoints.

### Reviewer question
Approve switching the ABTC1603 `pfs_stat` rule to
`1 iff (Days to Progression non-null) OR (Vital Status = "DEAD")`?

### If approved, tell Claude
In `scripts/extractors/abtc1603.py`, change the `pfs_stat` derivation:
```
pfs_stat = 1 if (pd.notna(row["Days to Progression"]) or row["Vital Status"].upper() == "DEAD") else 0
```
Use `extraction_method=derived_pfs_stat_progression_or_death`. Document the rule in YAML notes.
Rerun pipeline; expected drop of 15 `pfs_stat` mismatches and 3 `pfs_bin` mismatches.

---

## 14. 14C0059G bulk new-trial gaps (age, arm, phase, Collection_Event_alt)
**Affected entries:** 92 cells (23 rows × 4 fields)
**Priority:** P2
**Status:** missing source files

### Why this matters
Same root cause as item 3 but smaller scale. 14C0059G's source bundle lacks age, arm, and phase
columns, and no CE-alt mapping is configured. (Item 5 already covers `Cimac.id`; item 14 here
covers everything else.)

### Representative example
- trial: 14C0059G
- field(s): age, arm, phase, Collection_Event_alt
- cimac_part_id: CA44RBE
- Cimac.id: (NaN — see item 5)
- Collection_Event: DAY 60
- Edgar/template value: (no template — new trial)
- pipeline value: NaN
- source file path checked: `14C0059G-clinical/patient_demographics_all.csv` (no age column),
  `14C0059G-clinical/enrollment.csv`, `14C0059G-clinical/research_sample_collection_apheresis.csv`
- source column/field: (no Age column; no arm/phase/CE-alt mapping)
- source value or short quote (flagged_for_review.csv):
  `14C0059G demographics has no age column — flag for review`;
  `14C0059G arm not derivable from source`;
  `raw_ce='DAY 60': no mapping configured for 14C0059G`

### Interpretation
The 14C0059G source bundle was delivered without demographic age (PHI-stripped) or
enrollment-by-arm information. CE-alt strings ("DAY 60", "DAY 30", etc.) need a confirmed
mapping table.

### Reviewer question
Can the protocol team supply age (or confirm NA is acceptable), arm assignment, study phase,
and a `Collection_Event_alt` mapping for 14C0059G?

### If approved, tell Claude
Add new files to `14C0059G-clinical.sources` in YAML. Add
`14C0059G-clinical.collection_event_alt_map` and `14C0059G-clinical.trial_constants` (phase,
arm if single-arm). Update `scripts/extractors/nih_14c0059g.py` for any new columns. Rerun.

---

## 15. 10026 `treatment` residuals (template NaN; pipeline trial-constant)
**Affected entries:** 7 cells (`treatment` mismatches; `mismatch_kind=missing_in_template`)
**Priority:** P3
**Status:** likely template anomaly

### Why this matters
10026 has a single combination treatment (`ipi_aza`). The pipeline fills every row with this
trial constant; the template left 7 rows blank.

### Representative example
- trial: 10026
- field(s): treatment
- cimac_part_id: CBUP3C3
- Cimac.id: CBUP3C3JV.01
- Collection_Event: Baseline
- Edgar/template value: NaN
- pipeline value: `ipi_aza`
- source file path: `scripts/config/harmonization_config.yaml` (10026 `trial_constants.treatment`)
- source column/field: trial constant
- source value or short quote: provenance: `source_file=CONFIG:trial_constants`, `extraction_method=trial_constant`

### Interpretation
The 7 blanks in the template appear to be data-entry omissions — every 10026 patient received
the same combination per protocol.

### Reviewer question
Add these 7 rows to `template_anomalies.csv` (preferred — the pipeline is protocol-correct),
or revert the trial-constant for 10026 and emit NaN to match the template byte-for-byte?

### If approved, tell Claude
**Default (template anomaly):** add the 7 rows to `template_anomalies.csv` via the generator
in `scripts/generate_review_report.py`. No code change.

---

## 16. CIMAC-gu16257 `pfs_time` fallback edge cases (RECCUR / CLCRFL refinement)
**Affected entries:** 6 cells (4 `pfs_time` + 2 `pfs_bin`)
**Priority:** P3
**Status:** source-codebook ambiguity

### Why this matters
The committed GU16-257 `pfs_time` fallback is `DFSTIM if non-null else DRFSTIM` (documented in
`gu16257_pfs_time_fallback_investigation.md`). It fails for 4 rows where `DFSTIM` is non-null
but the template kept `pfs_time=NaN` (likely because `RECCUR` is `'N'`), and for 2 rows where the
template kept NaN despite a valid `DFSTIM` (`CM5PWSN` with `RECCUR='N'`, `CLCRFL='N'`).

### Representative example
- trial: CIMAC-gu16257
- field(s): pfs_time
- cimac_part_id: CM5PWSN
- Cimac.id: CM5PWSNLN.01
- Collection_Event: C1D1
- Edgar/template value: NaN
- pipeline value: 154
- source file path: `GU16-257-clinical/response.2023-01-04.csv`
- source column/field: `DFSTIM`, `DRFSTIM`, `RECCUR`, `CLCRFL`
- source value or short quote: `DFSTIM=154`, `DRFSTIM=NaN`, `RECCUR='N'`, `CLCRFL='N'`

### Interpretation
The template treats DFSTIM-non-null as `pfs_time` only when `RECCUR` is also non-null
(or equivalently, when there has been a recorded recurrence). Otherwise it kept NaN.

### Reviewer question
Approve refining the fallback to:
`DFSTIM if RECCUR non-null else DRFSTIM if DRFSTIM non-null else NaN`?

### If approved, tell Claude
In `scripts/extractors/gu16_257.py`, update the `pfs_time` extractor to require `RECCUR`
non-null before accepting `DFSTIM`. Use `extraction_method=value_with_fallback_RECCUR_gated`
and update the notes string accordingly. Rerun pipeline; expected to close 6 cells.

---

## 17. ABTC1603 `treatment` residuals (template NaN; pipeline trial-constant)
**Affected entries:** 3 cells
**Priority:** P3
**Status:** likely template anomaly

### Why this matters
Same pattern as item 15 (10026): pipeline emits the trial-constant `AdvtK_Val_Nivo_TMZ`; template
left 3 rows blank.

### Representative example
- trial: ABTC1603
- field(s): treatment
- cimac_part_id: CG07TB8
- Cimac.id: CG07TB82S.01
- Collection_Event: Baseline
- Edgar/template value: NaN
- pipeline value: `AdvtK_Val_Nivo_TMZ`
- source file path: `scripts/config/harmonization_config.yaml` (ABTC1603 trial_constants)
- source column/field: trial constant
- source value or short quote: provenance: `extraction_method=trial_constant`

### Interpretation
Same as item 15. Likely data-entry omissions.

### Reviewer question
Add these 3 rows to `template_anomalies.csv` (preferred) or revert trial-constant for ABTC1603?

### If approved, tell Claude
**Default:** add the 3 rows to `template_anomalies.csv` via the generator in
`scripts/generate_review_report.py`. No code change.

---

## 18. CIMAC-9204 `race` "Other" → `unk`
**Affected entries:** 2 cells (1 patient × 2 timepoints)
**Priority:** P3
**Status:** YAML value-map gap (one-line add)

### Why this matters
Patient CD5Z9AG has source `itmRace ~ Race = "Other"`. The global value-map has
`Unknown → unk` but no `Other → unk`; the pipeline passes "Other" through unmapped and the
confidence threshold drops the cell to NaN. The template normalized to `unk`.

### Representative example
- trial: CIMAC-9204
- field(s): race
- cimac_part_id: CD5Z9AG
- Cimac.id: CD5Z9AGFT.01
- Collection_Event: Baseline
- Edgar/template value: `unk`
- pipeline value: NaN
- source file path: `9204-clinical/demographics_dose_level.ipilimumab_2024-05-01.csv`
- source column/field: `itmRace ~ Race`
- source value or short quote: `itmRace ~ Race = "Other"`

### Interpretation
A one-line YAML addition closes both cells.

### Reviewer question
Approve adding `Other → unk` to `value_normalizations.race`?

### If approved, tell Claude
In `harmonization_config.yaml`, under `value_normalizations.race.unk`, append `Other`
(confidence 0.85). Rerun pipeline; expected to close 2 cells.

---

## 19. CIMAC-9204 `Collection_Event_alt` `Day_8` → `C2`
**Affected entries:** 2 cells
**Priority:** P3
**Status:** YAML mapping disagrees with template

### Why this matters
Current YAML: `9204-clinical.collection_event_alt_map.Day_8 = "Baseline"`.
Template: `Day_8 → "C2"`.

### Representative example
- trial: CIMAC-9204
- field(s): Collection_Event_alt
- cimac_part_id: CD5ZVSK
- Cimac.id: CD5ZVSKVR.01
- Collection_Event: Day_8
- Edgar/template value: `C2`
- pipeline value: `Baseline`
- source file path: `scripts/config/harmonization_config.yaml`
- source column/field: `9204-clinical.collection_event_alt_map`
- source value or short quote: YAML currently `Day_8: Baseline`

### Interpretation
Clinically, Day_8 (cycle-2 start in 9204) is a "C2" timepoint, not a baseline.

### Reviewer question
Approve changing `9204-clinical.collection_event_alt_map.Day_8` from `Baseline` to `C2`?

### If approved, tell Claude
In `harmonization_config.yaml`, change the YAML mapping. Rerun pipeline; expected to close 2 cells.

---

## 20. CIMAC-9204 age (single patient; integer vs integer)
**Affected entries:** 1 cell
**Priority:** P3
**Status:** likely template anomaly (single-patient typo)

### Why this matters
One row: template `age=68`, source `Age at Enrollment=64`. Other 64 rows match perfectly. Most
likely a transcription typo in the template.

### Representative example
- trial: CIMAC-9204
- field(s): age
- cimac_part_id: CD5Z7O5
- Cimac.id: CD5Z7O5RL.01
- Collection_Event: Baseline
- Edgar/template value: 68
- pipeline value: 64
- source file path: `9204-clinical/demographics_dose_level.ipilimumab_2024-05-01.csv`
- source column/field: `Age at Enrollment`
- source value or short quote: `Age at Enrollment=64`

### Interpretation
Single-patient mismatch with the source clearly showing 64. Pipeline is source-faithful.

### Reviewer question
Add this 1 row to `template_anomalies.csv` (preferred) or treat as unresolved?

### If approved, tell Claude
**Default:** add the 1 row to `template_anomalies.csv`. No code change.

---

## Coverage matrix — which validation-summary rows are accounted for

Every non-perfect (trial, column) row in `validation_summary.csv` is mapped to one of the items
above:

| Trial         | Column                | Mismatches | Item(s)       |
|---------------|-----------------------|-----------:|---------------|
| CIMAC-s1400i  | age                   | 561        | 4             |
| 10026         | BOR.binary            | 54         | 9 + 11        |
| 10104         | os_time               | 40         | 7             |
| 10026         | bor_bin               | 36         | 9 cascade     |
| 10104         | os_stat               | 17         | 8             |
| 10104         | BOR.binary            | 17         | 7 cascade + 8 |
| ABTC1603      | pfs_stat              | 15         | 13            |
| 10104         | pfs_time              | 14         | 7             |
| CIMAC-e4412   | pfs_time              | 11         | 10            |
| 10104         | BOR                   | 9          | 8             |
| CIMAC-e4412   | os_time               | 8          | 10            |
| CIMAC-e4412   | BOR.binary            | 8          | 12            |
| CIMAC-e4412   | BOR                   | 8          | 12            |
| 10026         | treatment             | 7          | 15            |
| 10104         | pfs_bin               | 7          | 7 cascade     |
| 10104         | bor_bin               | 7          | 7 cascade     |
| CIMAC-gu16257 | pfs_time              | 4          | 16            |
| ABTC1603      | pfs_bin               | 3          | 13 cascade    |
| ABTC1603      | treatment             | 3          | 17            |
| CIMAC-9204    | Collection_Event_alt  | 2          | 19            |
| CIMAC-9204    | race                  | 2          | 18            |
| CIMAC-gu16257 | pfs_bin               | 2          | 16 cascade    |
| CIMAC-9204    | age                   | 1          | 20            |

Total cells: 836 mismatches accounted for.

New-trial flagged groups also covered: 10013 (12 fields × 196 rows), 14C0059G (12 fields × 23
rows). Trial-constant phase NA for 10026/10104/9204/e4412 is an expected design choice (template
left phase blank for these trials), not a discrepancy.
