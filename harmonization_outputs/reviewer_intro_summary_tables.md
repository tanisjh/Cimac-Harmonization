# Reviewer intro summary — slide-deck-ready material

Generated 2026-05-20 as read-only reviewer material to sit near the front of
the discrepancy slide deck. No code, config, harmonized CSVs, or pipeline
outputs were modified to produce this document.

Source artifacts: `validation_summary.csv`, `validation_report.csv`,
`provenance_long.csv`, `harmonized_11trials.csv`, `harmonized_9trials_reproduced.csv`,
`final_handoff_report.md`, `top_review_items_with_source_evidence.md`,
`expanded_reviewer_examples_draft.md`, `scripts/config/harmonization_config.yaml`,
`scripts/lib/normalize.py`, and the per-trial extractors under
`scripts/extractors/`.

**Scope.** 11 trials harmonized (BACCI excluded). 9 of them have an Edgar
template to validate against; 2 (10013, 14C0059G) are new trials with no
template. `exclusion_and_order_checks.txt` → `VERDICT: PASS`. Overall match
rate against the 9-trial template: **25,879 / 26,715 cells = 96.87%** across
9 trials × 15 measurable columns.

---

## Part 1 — 9-trial comparison summary tables

### Table 1.1 — Detailed match table (9 trials × 15 fields)

Cells show **match rate** with **(mismatch count)** when below 1.000. A `1.000`
cell is a perfect match against the Edgar template. `n_rows` is the count of
template rows in the trial. Totals at the bottom.

| trial | n_rows | age | sex | race | arm | treatment | phase | Collection_Event_alt | BOR | BOR.binary | bor_bin | pfs_time | pfs_stat | pfs_bin | os_time | os_stat | trial mismatches |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---:|
| **10026**          | 214 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 (7) | 1.000 | 1.000 | 1.000 | **0.748 (54)** | **0.832 (36)** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | **97** |
| **10104**          | 213 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000     | 1.000 | 1.000 | 0.958 (9) | 0.920 (17)   | 0.967 (7)      | 0.934 (14) | 1.000 | 0.967 (7) | **0.812 (40)** | 0.920 (17) | **111** |
| **ABTC1603**       | 148 | 1.000 | 1.000 | 1.000 | 1.000 | 0.980 (3) | 1.000 | 1.000 | 1.000     | 1.000        | 1.000          | 1.000      | **0.899 (15)** | 0.980 (3) | 1.000 | 1.000 | **21** |
| **CIMAC-10021**    | 154 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000     | 1.000 | 1.000 | 1.000     | 1.000        | 1.000          | 1.000      | 1.000 | 1.000 | 1.000 | 1.000 | **0** |
| **CIMAC-9204**     |  65 | 0.985 (1) | 1.000 | 0.969 (2) | 1.000 | 1.000 | 1.000 | 0.969 (2) | 1.000     | 1.000        | 1.000          | 1.000      | 1.000 | 1.000 | 1.000 | 1.000 | **5** |
| **CIMAC-e4412**    | 167 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000     | 1.000 | 1.000 | 0.952 (8) | 0.952 (8)    | 1.000          | 0.934 (11) | 1.000 | 1.000 | 0.952 (8) | 1.000 | **35** |
| **CIMAC-gu16257**  | 196 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000     | 1.000 | 1.000 | 1.000     | 1.000        | 1.000          | 0.980 (4)  | 1.000 | 0.990 (2) | 1.000 | 1.000 | **6** |
| **CIMAC-s1400i**   | 561 | **0.000 (561)** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000     | 1.000        | 1.000          | 1.000      | 1.000 | 1.000 | 1.000 | 1.000 | **561** |
| **EAY131_Z1D**     |  63 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000     | 1.000 | 1.000 | 1.000     | 1.000        | 1.000          | 1.000      | 1.000 | 1.000 | 1.000 | 1.000 | **0** |
| **All trials (total)** | **1,781** | 561 mis | 0 | 2 | 0 | 10 | 0 | 2 | 17 | **79** | 43 | 29 | 15 | 9 | **48** | 17 | **836** |

Notes
- The 561 CIMAC-s1400i `age` cells are a **deliberate NA** — decimal age was truncated at the CIDC step and cannot be recovered from any S1400I source file (see decision D5). Pipeline emits NA + flag; template carries the lost decimal value. This is the single largest source of mismatches (67% of the 836 total).
- The 36 `bor_bin` mismatches on 10026 are a **direct downstream consequence** of the 10026 CRm/CRi → R rule (D3a): the rule turns those rows' BOR.binary from `CRm`/`CRi` to `R`, which then resolves `bor_bin = 1` while the template kept `NaN`. They are a trade-off, not a pipeline error.
- The 7 `bor_bin` and 7 `pfs_bin` mismatches on 10104 are downstream of the 14 `pfs_time` mismatches via the 120-day rule.

### Table 1.2 — Compact slide-friendly view (trials × 5 domains)

One cell per (trial, domain). Cells with no mismatches show `✓ 1.000`. Cells
with any mismatch show **worst (n=mismatches)** and the field driving it.

| trial | n_rows | Demographics (age, sex, race) | Trial metadata (arm, treatment, phase, CE_alt) | Response (BOR, BOR.binary, bor_bin) | PFS (pfs_time, pfs_stat, pfs_bin) | OS (os_time, os_stat) | trial total mismatches |
|---|---:|---|---|---|---|---|---:|
| **10026**         | 214 | ✓ 1.000 | 0.967 / 7 (treatment) | **0.748 / 54** (BOR.binary CRm/CRi) | ✓ 1.000 | ✓ 1.000 | **97** |
| **10104**         | 213 | ✓ 1.000 | ✓ 1.000 | 0.920 / 17 (BOR.binary) | 0.934 / 14 (pfs_time) | **0.812 / 40** (os_time) | **111** |
| **ABTC1603**      | 148 | ✓ 1.000 | 0.980 / 3 (treatment) | ✓ 1.000 | **0.899 / 15** (pfs_stat) | ✓ 1.000 | **21** |
| **CIMAC-10021**   | 154 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | **0** |
| **CIMAC-9204**    |  65 | 0.969 / 3 (race, age) | 0.969 / 2 (CE_alt) | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | **5** |
| **CIMAC-e4412**   | 167 | ✓ 1.000 | ✓ 1.000 | 0.952 / 16 (BOR, BOR.binary) | 0.934 / 11 (pfs_time) | 0.952 / 8 (os_time) | **35** |
| **CIMAC-gu16257** | 196 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | 0.980 / 6 (pfs_time, pfs_bin) | ✓ 1.000 | **6** |
| **CIMAC-s1400i**  | 561 | **0.000 / 561** (age — NA by policy) | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | **561** |
| **EAY131_Z1D**    |  63 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | **0** |

Reading guide
- `✓ 1.000` = every row matches the template for every field in that domain.
- `0.xxx / N` = lowest match rate in the domain, with `N` total mismatching cells across all fields in the domain.
- Two trials (**CIMAC-10021** and **EAY131_Z1D**) are perfect across all 15 fields.
- Three trials (**ABTC1603**, **CIMAC-9204**, **CIMAC-gu16257**) have only small residuals; each can be closed with one or two YAML / extractor edits per decision items D8, D13, D14, D15.
- The two large blocks are **CIMAC-s1400i age** (policy NA) and **10026 BOR.binary + bor_bin** (CRm/CRi pass-through trade-off, D3a/D9).

### Table 1.3 — Mismatches grouped by root cause

| root cause | trials affected | mismatching cells | next step | decision id |
|---|---|---:|---|---|
| S1400I `age` decimal truncated upstream at CIDC | CIMAC-s1400i | 561 | Supply un-truncated SWOG age **OR** substitute `age_num` **OR** accept NA | D5 |
| 10026 CRm/CRi → R trade-off (D3a in effect) | 10026 | 54 (BOR.binary) + 36 (bor_bin) = 90 | Keep R-mapping and add 54 rows to `template_anomalies.csv` **OR** switch to pass-through | D9 |
| 10104 per-patient OS/PFS anchor disagreement | 10104 | 40 (os_time) + 17 (os_stat) + 14 (pfs_time) + 17 (BOR.binary) + 9 (BOR) + 7 (bor_bin) + 7 (pfs_bin) = 111 | Implement conditional anchor (use `tx_phase_end_dt` for crossover / off-treatment patients) | D7 |
| ABTC1603 `pfs_stat` ignores death-without-progression | ABTC1603 | 15 (pfs_stat) + 3 (pfs_bin) = 18 | Switch rule to `1 iff progression OR DEAD` | D8 |
| E4412 `BOR` "Unevaluable [<reason>]" labels | CIMAC-e4412 | 8 (BOR) + 8 (BOR.binary) = 16 | Add `contains: "Unevaluable"` rule | D11 |
| E4412 month→day rounding | CIMAC-e4412 | 11 (pfs_time) + 8 (os_time) = 19 | Switch `round()` → `int()` truncation | D10 |
| GU16-257 fallback edge case (RECCUR=NaN) | CIMAC-gu16257 | 4 (pfs_time) + 2 (pfs_bin) = 6 | Require RECCUR non-null in fallback | D13 |
| 10026 / ABTC1603 treatment residuals | 10026, ABTC1603 | 7 + 3 = 10 | Spot-check; likely template omissions | — |
| 9204 `Other → unk` and `Day_8 → C2` | CIMAC-9204 | 2 (race) + 2 (CE_alt) + 1 (age) = 5 | One-line YAML each | D14, D15 |
| **Total** |  | **836** |  |  |

---

## Part 2 — Rules currently implemented in code

Read-only audit of `scripts/config/harmonization_config.yaml`,
`scripts/lib/normalize.py`, and the per-trial extractors in
`scripts/extractors/`. Each rule below was verified to be currently in
effect in the most recent pipeline run.

| rule_id | field(s) | trial scope | current rule | where implemented | source / evidence basis | status | downstream impact | reviewer question |
|---|---|---|---|---|---|---|---|---|
| **R1 — pfs_bin 120-day landmark** | `pfs_bin` | All 9 template trials + 2 new (pipeline-wide; **2,000** cells use `extraction_method=derived_pfs_bin_120d`) | `pfs_bin = 1 iff pfs_time ≥ 120; 0 iff pfs_time < 120 AND pfs_stat == 1; NaN iff pfs_time < 120 AND pfs_stat == 0` | YAML `derived_rules.pfs_bin_landmark_days: 120` (line 43); `scripts/lib/normalize.py::derive_pfs_bin` (lines 132–171) | Empirical fit: 100% match on the 9-trial template at landmark=120; no SAP/codebook in repo defines it | **Implemented, needs reviewer confirmation** | Required input to "pfs benefit ≥ 4 mo" downstream analyses; touches every row | Confirm 120-day landmark vs SAP; if confirmed, drop the "pending final clinical confirmation" suffix from provenance notes |
| **R2 — bor_bin 120-day SD landmark** | `bor_bin` | All 9 template trials + 2 new (pipeline-wide; **2,000** cells use `extraction_method=derived_bor_bin_120d`) | `bor_bin = 1 iff BOR.binary == 'R' OR (BOR.binary == 'SD' AND pfs_time ≥ 120); 0 iff BOR.binary == 'NR' OR (BOR.binary == 'SD' AND pfs_time < 120); NaN otherwise (other/CRm/CRi-via-pre-D3a/unrecognized/NaN)` | YAML `derived_rules.bor_bin_landmark_days: 120` (line 42); `scripts/lib/normalize.py::derive_bor_bin` (lines 90–129) | Empirical fit: 100% match on all 9 trials at landmark=120 after the CRm/CRi → R rule; no SAP/codebook in repo defines it | **Implemented, needs reviewer confirmation** | Identifies clinical-benefit responders; touches every row | Confirm 120-day SD landmark vs SAP |
| **R3 — Global BOR.binary mapping** | `BOR.binary` | Pipeline-wide | `R bucket`: CR, PR, UPR, Complete Response, Partial Response, Unconfirmed Partial Response, Clin-Ben, Clinical Benefit, Y (GU16-257), Morphological Complete Remission (9204), Partial Remission (9204), **CRm, CRi, CR with MRD-, CR with incomplete count recovery (10026)**.  `SD bucket`: SD, STA, Stable, Stable Disease.  `NR bucket`: PD, Progressive Disease, Progressive Disease or Relapsed Disease, SYMP, Symptomatic Deterioration, INC, Inconclusive, NASS, Not Assessable, No C-B, No Clinical Benefit, N (GU16-257), Persistent Disease (9204), Progression (9204).  `other bucket`: UE, Unevaluable, NE, Not Applicable.  Unmatched values → NaN. | YAML `value_normalizations.BOR.binary` (lines 717–750); `scripts/lib/normalize.py::derive_bor_binary` (lines 58–68) | Trial-by-trial codebook citations enumerated in `final_handoff_report.md` § 4 | **Implemented, source-supported** | Drives `bor_bin` (R2); affects clinical-benefit endpoint | None for the core mapping (see R4 for the contested sub-decision) |
| **R4 — 10026 CRm/CRi → R** | `BOR.binary`, downstream `bor_bin` | 10026 only (36 rows affected) | CRm, CRi, "CR with MRD-", "CR with incomplete count recovery" all map to `R`. Edgar's template preserves the literal short codes `CRm`/`CRi`. | YAML `value_normalizations.BOR.binary.R` (lines 732–740) | 10026 Data Dictionary `Sheet1` rows 92–94: `CR = Morphologic Complete Remission`, `CRi = Morphologic CR w/ Incomplete Blood Count Recovery`, `CRm = Bone Marrow CR` (all forms of complete remission) | **Current rule, under review** (D9) | Closes the 10026 `bor_bin` SD-landmark gap (huge clinical-benefit win); creates 54 residual `BOR.binary` and 36 residual `bor_bin` mismatches against the template | Keep R-mapping and add 54 entries to `template_anomalies.csv`, **or** revert to pass-through (CRm/CRi kept verbatim, `bor_bin` reverts to NaN on 36 rows)? |
| **R5 — 10104 OS/PFS anchor** | `os_time`, `pfs_time` (and downstream `os_stat`, `BOR.binary`, `bor_bin`, `pfs_bin`) | 10104 only | Pipeline uses the single column `"...from first_cycle_first_day to DEATH_DT or last_follow_up_date"` for OS and the analogous PFS column **unconditionally** for all patients (Arm A/B file) and the analogous columns from the Arm C file. | YAML `10104-clinical.response_columns_aandb` (lines 388–393) and `response_columns_armc` (lines 394–399); `scripts/extractors/nci_10104.py` (lines 168–185) | P1#1 finding: the chosen anchor matches the template at ~83%; the original `PT_REG_DT_INT` anchor matched at only ~9% (Arm A/B) or ~20% (Arm C) | **Current rule, under review** (D7) | 40 os_time + 14 pfs_time + 17 os_stat + 17 BOR.binary + 9 BOR + 7 bor_bin + 7 pfs_bin mismatches (111 cells) | **Not yet implemented.** Approve switching to a per-patient conditional anchor: use `tx_phase_end_dt` for crossover / off-treatment patients (e.g., when `Date_of_treatment Cross Over from Arm B to Arm C` is non-null), survival columns otherwise? |
| **R6 — ABTC1603 pfs_stat** | `pfs_stat` (and downstream `pfs_bin`) | ABTC1603 only (15 rows mismatched) | `pfs_stat = 1 iff Days to Progression is non-null, else 0` (progression-only convention). Death without progression is currently coded `pfs_stat = 0`. | `scripts/extractors/abtc1603.py` lines 171–179 (`derived_from_nonnull`) | Source columns: `Days to Progression`, `Vital Status` in `abtc_1603_treatmentresponse_03042024_2024-04-17.csv` | **Current rule, under review** (D8) | 15 pfs_stat + 3 pfs_bin mismatches (18 cells) | **Not yet implemented.** Approve switching to the standard oncology convention `pfs_stat = 1 iff (Days to Progression non-null) OR (Vital Status == 'DEAD')`? |
| **R7 — E4412 time conversion (months → days)** | `os_time`, `pfs_time` | CIMAC-e4412 only | `days = round(months × 30.4375)` where `months` = source `os_wk`/`pfs_wk` (despite the "_wk" suffix, source values empirically encode months — Codebook description "years" is also wrong; the ×30.4375 fit reproduces template days exactly modulo rounding). | YAML `E4412-clinical.time_unit_conversion.{os_time,pfs_time}: 30.4375` (lines 518–523); `scripts/extractors/e4412.py` line 62 (`round(v * float(time_conv.get(target, 7.0)))`) | Empirical fit: 0.41889 × 30.4375 ≈ 12.75 ≈ template 13 for C29Z0FX | Implemented, source-supported; **rounding strategy under review** (D10) | All 19 mismatches (11 pfs_time + 8 os_time) are off-by-1 day | **Uses `round()`, not `int()`.** Approve switching to `int(months × 30.4375)` truncation to match the template? |
| **R8 — GU16-257 pfs_time fallback** | `pfs_time` (and downstream `pfs_bin`) | CIMAC-gu16257 only | First non-null of `[DFSTIM, DRFSTIM]`. RECCUR (recurrence Y/N) is **not** currently consulted by the fallback. | YAML `GU16-257-clinical.pfs_time_fallback_columns: ["DFSTIM", "DRFSTIM"]` (line 295); `scripts/extractors/gu16_257.py` lines 116–139 (`value_with_fallback`) | Matches 192/196 (0.980) of the template; documented in `gu16257_pfs_time_fallback_investigation.md` | Implemented, source-supported; **edge cases under review** (D13) | 4 pfs_time + 2 pfs_bin mismatches (6 cells) | Approve refining the fallback to require RECCUR non-null before accepting DFSTIM (would convert the 2 CM5PWSN rows to NaN and close the residual `pfs_bin` mismatches)? |
| **R9 — Trial constants for treatment/phase/arm** | `treatment`, `phase`, `arm` | Per-trial (see config) | **EAY131_Z1D**: `treatment="Nivolumab"`, `phase="II"`. **S1400I**: `arm="Others"` (template hard-codes for all 561 rows), `treatment` via cross-tab from `ARMNAME`, `phase` derived from `cimac_part_id` prefix (CCZR→A, CNKA→B). **ABTC1603**: `treatment="AdvtK_Val_Nivo_TMZ"`, `BOR.binary="other"` (template constant for all 148 rows). **10026**: `treatment="ipi_aza"`. **GU16-257**: `treatment="gem+cis+nivo"`, `arm="Others"`. **10021**: `arm="Others"`. **9204**: `arm="Others"`, `treatment` per file membership (ipi or nivo demographics file). **E4412**: `arm="Others"`, `treatment` per letter code A–I. **10104**: `treatment` per `arm_code` cross-tab. **10013** (new): `treatment="pembrolizumab+NACT"`. **14C0059G** (new): `treatment="adoptive_cell_therapy"`. | YAML per-trial `trial_constants` blocks; some per-arm via `treatment_per_arm` / `treatment_by_file_key` | Cross-tab + Codebook for each trial (see `final_handoff_report.md` § 4) | Implemented, source-supported | Drives the trial_metadata domain; touches every row in scope | Residual mismatches are limited to: 10026 treatment 7 cells, ABTC1603 treatment 3 cells. Confirm they're template omissions → `template_anomalies.csv`? |
| **R10 — Collection_Event_alt per-trial mappings** | `Collection_Event_alt` | Per-trial (see config) | Per-trial `collection_event_alt_map` blocks, e.g. **10026**: End_of_Cycle_7→C8, End_of_Cycle_10→C12, Other→EOT. **9204**: Day_8→Baseline (only 2 rows). **EAY131_Z1D**: End_of_treatment→C3. **S1400I**: Progression/Other→EOT. **ABTC1603, GU16-257, E4412, 10021, 10104**: per-trial maps. **10013, 14C0059G**: no map (all NA + flagged). | YAML per-trial `collection_event_alt_map` blocks | Direct template cross-tab | Implemented, source-supported; **two small items under review** (D15 for 9204; 10013/14C0059G map open) | 2 CE_alt mismatches on 9204 (Day_8); 196 + 23 = 219 ALL_NA on the two new trials (completeness gap, not a discrepancy) | D15: change 9204 `Day_8 → C2` (one-line YAML). For 10013/14C0059G: supply the bucket map once sample manifests arrive |
| **R11 — Missing-value / low-confidence policy** | All fields | Pipeline-wide | If an extracted cell's confidence falls below the per-field threshold in `confidence_thresholds.per_field` (defaults: cimac_part_id/Cimac.id=1.00, BOR/pfs_time/race/os_time=0.70, sex/age/os_stat/pfs_stat/Collection_Event/bor_bin/pfs_bin=0.80, arm=0.50, treatment=0.60, phase=0.50, default=0.70), the cell is **NA** in the harmonized CSV and a row is written to `flagged_for_review.csv` with the proposed mapping, observed values, reason, and a reviewer question. **No silent guessing.** | YAML `confidence_thresholds` (lines 67–87); `scripts/lib/extractor_base.py`; `scripts/lib/provenance.py` | Project policy (see `feedback_uncertainty_policy.md` in memory and `README.txt` "no_silent_guessing") | Implemented, source-supported | 4,542 cells currently below threshold → NA + flagged (down from 7,126 before the 120-day rules) | Confirm the per-field thresholds; in particular `bor_bin`/`pfs_bin` at 0.80 may want to drop once R1/R2 are formally confirmed |

### Stale documentation flag
- The pre-existing `README.txt` (§ "KNOWN UNRESOLVED ITEMS") and `final_handoff_report.md` (§ 3, § 5) **still describe `bor_bin` and `pfs_bin` as "NOT committed" with a candidate "183-day / clinical-benefit 6-month-PFS" rule**. Both predate the 120-day rollout. The authoritative current state is the YAML `derived_rules` block and `scripts/lib/normalize.py`, both of which use **120 days**. `PROJECT_HANDOFF_CURRENT_STATE.md` (last refreshed 2026-05-20) reflects the 120-day rule correctly.

---

## Part 3 — Slide-ready content (4 intro slides)

### Slide A — "Overall comparison to Edgar's 9-trial template"

**Title:** Overall comparison to Edgar's 9-trial template

**Subtitle / one-line takeaway:** 96.87% cell-level match across 1,781 rows × 15 fields; 2 of 9 trials are perfect; ~67% of remaining mismatches are explained by 4 named items.

**Body (use Table 1.2 compact view):**

| trial | n | Demographics | Trial metadata | Response | PFS | OS |
|---|---:|---|---|---|---|---|
| 10026         | 214 | ✓ 1.000 | 0.967 / 7 | **0.748 / 54** | ✓ 1.000 | ✓ 1.000 |
| 10104         | 213 | ✓ 1.000 | ✓ 1.000 | 0.920 / 17 | 0.934 / 14 | **0.812 / 40** |
| ABTC1603      | 148 | ✓ 1.000 | 0.980 / 3 | ✓ 1.000 | **0.899 / 15** | ✓ 1.000 |
| CIMAC-10021   | 154 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 |
| CIMAC-9204    |  65 | 0.969 / 3 | 0.969 / 2 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 |
| CIMAC-e4412   | 167 | ✓ 1.000 | ✓ 1.000 | 0.952 / 16 | 0.934 / 11 | 0.952 / 8 |
| CIMAC-gu16257 | 196 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | 0.980 / 6 | ✓ 1.000 |
| CIMAC-s1400i  | 561 | **0.000 / 561** (age — policy NA) | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 |
| EAY131_Z1D    |  63 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 | ✓ 1.000 |

**Speaker notes:**
- `✓ 1.000` = every row matches the template for every field in that domain.
- `0.xxx / N` = lowest match rate, with N total mismatching cells across the domain.
- 561 of the 836 total mismatches are CIMAC-s1400i `age` (decimal age truncated upstream at CIDC; not recoverable from any source file in the trial dir).
- 90 are the 10026 CRm/CRi trade-off (BOR.binary 54 + bor_bin 36) — a deliberate decision under D9.
- The remaining ~185 are clustered into ~6 named items, each with strong source evidence and a one-decision fix.

---

### Slide B — "Rules already implemented; reviewer confirmation requested"

**Title:** Rules already implemented; reviewer confirmation requested

**Subtitle:** Three high-impact rules are in effect across all rows. They are not unresolved discrepancies — we are asking for clinical confirmation.

| # | rule | scope | what it does | why we want confirmation |
|---|---|---|---|---|
| **1** | **pfs_bin 120-day landmark** | All 2,000 rows | `pfs_bin = 1` if pfs_time ≥ 120; `= 0` if pfs_time < 120 AND pfs_stat = 1; `= NaN` if pfs_time < 120 AND pfs_stat = 0 | Reproduces Edgar's column at ~99% across all template trials; no SAP/codebook in repo defines the landmark. Match rate jumped from ~9% → ~99% after rollout. |
| **2** | **bor_bin 120-day SD landmark** | All 2,000 rows | `bor_bin = 1` if BOR.binary = R OR (SD AND pfs_time ≥ 120); `= 0` if NR OR (SD AND pfs_time < 120); `= NaN` otherwise | Reproduces Edgar's column at 100% on every applicable trial. Match rate jumped from ~30% → ~99% after rollout. |
| **3** | **10026 CRm / CRi → R** | 10026 (36 rows) | CRm (Bone Marrow CR), CRi (Morphologic CR w/ incomplete count recovery), "CR with MRD-", "CR with incomplete count recovery" all map to `R` in BOR.binary | Closes the 10026 SD-landmark gap. Edgar preserves the literal short codes verbatim — we believe that is a template anomaly, not a clinical signal. 10026 Data Dictionary `Sheet1` rows 92–94 supports the R-mapping. |

**Speaker notes:**
- Rules 1 and 2 touch every row in the dataset. Confirm them and we drop the "pending final clinical confirmation" suffix from provenance notes.
- Rule 3 is the contested one: keeping it adds 54 rows to `template_anomalies.csv`; reverting it returns 36 `bor_bin` cells to NaN.

---

### Slide C — "Rules currently in code"

**Title:** Rules currently in code

**Subtitle:** Per-trial extraction rules in effect today, beyond the three confirmation items.

| rule | trial(s) | what it does | status |
|---|---|---|---|
| Global BOR → BOR.binary mapping | all | CR/PR-like → R; SD-like → SD; PD-like → NR; Unevaluable → other; missing → NA | source-supported |
| 10104 OS/PFS anchor | 10104 | Uses `first_cycle_first_day → DEATH_DT or last_follow_up_date` for every patient (current rule matches ~83% of template) | **under review (D7)** — conditional `tx_phase_end_dt` for crossover / off-treatment **not yet implemented** |
| ABTC1603 pfs_stat | ABTC1603 | `pfs_stat = 1` iff `Days to Progression` non-null (progression-only) | **under review (D8)** — death-without-progression rule **not yet implemented** |
| E4412 time conversion | CIMAC-e4412 | `os_wk`/`pfs_wk` are actually months → `round(months × 30.4375)` days | source-supported; **rounding under review (D10)** — currently `round()`, proposed `int()` |
| GU16-257 pfs_time fallback | CIMAC-gu16257 | First non-null of `[DFSTIM, DRFSTIM]` (RECCUR not currently consulted) | source-supported; **RECCUR edge case under review (D13)** |
| Trial constants for treatment / phase / arm | per-trial | E.g., 10026 treatment = `ipi_aza`; ABTC1603 treatment = `AdvtK_Val_Nivo_TMZ`, BOR.binary = `other`; S1400I arm = `Others`; EAY131_Z1D phase = `II`, treatment = `Nivolumab` | source-supported |
| Collection_Event_alt mappings | per-trial | E.g., 10026 End_of_Cycle_10 → C12; 9204 Day_8 → Baseline | source-supported; **9204 Day_8 → C2 under review (D15)**; 10013 / 14C0059G no map (all flagged) |
| Missing-value / low-confidence policy | all | Below per-field threshold → NA + row in `flagged_for_review.csv` (no silent guessing) | implemented, source-supported |

**Speaker notes:**
- The bold "under review" rules each have **strong source evidence for the proposed change** but are not yet active. If the reviewers approve them, each is a one-line YAML or extractor change.
- 4,542 cells are currently NA + flagged (down from 7,126 before the 120-day rules). The threshold table is in `harmonization_config.yaml` and is itself reviewable.

---

### Slide D — "Remaining decisions before adding new rules"

**Title:** Remaining decisions before we add new rules

**Subtitle:** Twelve open items, grouped. Each has source evidence in `top_review_items_with_source_evidence.md`. Most are single-line config changes.

**Confirm already-implemented rules (Slide B items):**
- D1 — 120-day `pfs_bin` landmark (touches 2,000 cells)
- D2 — 120-day `bor_bin` SD landmark (touches 2,000 cells)
- D3 — 10026 CRm/CRi → R (D3a in effect; 36 + 54 cells)

**Decide on contested clinical conventions:**
- D7 — 10104 OS/PFS anchor: switch to per-patient conditional (`tx_phase_end_dt` for crossover / off-treatment), or accept residual? (~111 cells)
- D8 — ABTC1603 `pfs_stat`: count death-without-progression as event? (~18 cells)
- D9 — 10026 CRm/CRi pass-through vs R-mapping: keep R + add 54 anomalies, or revert? (~90 cells)

**Supply missing source files (cannot resolve without external input):**
- D4 — Sample manifests for 10013 and 14C0059G → `Cimac.id` (~219 cells)
- D5 — Un-truncated decimal `age` from SWOG for CIMAC-s1400i, or accept integer `age_num`, or accept NA (~561 cells)
- D6 — 10013 bulk new-trial gaps: survival CRFs, arm assignment, Collection_Event_alt bucket map, BOR pCR-text rule

**Surgical YAML / extractor edits (one-line each):**
- D10 — E4412 month→day conversion: `round()` → `int()` (~19 cells)
- D11 — E4412 `BOR` / `BOR.binary`: add `contains: "Unevaluable"` rule (~16 cells)
- D12 — 10104 `BOR` template anomalies (R005–R007): keep pipeline values + add 7 rows to `template_anomalies.csv` (~9 cells)
- D13 — GU16-257 `pfs_time` fallback: require RECCUR non-null (~6 cells)
- D14 — 9204 race: add `Other → unk` (2 cells)
- D15 — 9204 Collection_Event_alt: `Day_8 → C2` (2 cells)

**Speaker notes:**
- Approving Slide B items closes the 2,000-row confirmation backlog with no code change.
- D7 + D8 + the surgical edits would bring overall match rate from 96.87% to ~99%.
- D4/D5/D6 cannot be closed by code alone — they need data from SWOG or the protocol teams.

---

## Stale-documentation flags (for awareness; do not edit generated outputs)

- `README.txt`, "KNOWN UNRESOLVED ITEMS" section — describes `bor_bin` / `pfs_bin` as **NOT committed** and references a candidate 183-day / 6-month-PFS rule. This predates the 120-day rollout; the YAML, code, and provenance now reflect the **120-day committed rule** (per Slide B items 1 and 2).
- `harmonization_outputs/final_handoff_report.md`, sections 3 and 5 — same stale language ("NOT committed per the no-silent-guessing policy"). The file is auto-generated and is regenerated each pipeline run; the stale text should be updated in `scripts/build_final_handoff.py` (not by manual edit) when the 120-day rule is formally confirmed.
- `harmonization_outputs/expanded_reviewer_examples_draft.md`, slide for the 120-day `bor_bin` rule — still uses the older 10026 CBUPOJV example. `PROJECT_HANDOFF_CURRENT_STATE.md` § 5 / § 8 recommends replacing it with the cleaner CIMAC-s1400i CCZRAUC / CCZRY9C pair before producing the .pptx.

---

## Companion CSV

A flat per-(trial, field) version of Table 1.1 is at
`harmonization_outputs/reviewer_intro_summary_tables.csv`. Columns:
`trial, n_rows, field, domain, n_match, n_mismatch, match_rate, status`.
Use it to sort/filter or paste into a spreadsheet — every row in Tables 1.1,
1.2, and 1.3 is derivable from it.
