# Reviewer decisions — implementation plan (read-only)

Generated 2026-05-20 as a planning document. **No code, config, harmonized CSVs,
pipeline outputs, reports, or slide decks were modified.**

Inputs used:
- Bracketed reviewer decisions / TODOs from `cimac_to_do.pptx` (root, present
  on disk), authoritatively conveyed in the user message of this session
- James' two clarifications in the same message (BOR rename + 9204 `Day_8`
  mapping)
- `PROJECT_HANDOFF_CURRENT_STATE.md`, `harmonization_outputs/reviewer_intro_summary_tables.md`,
  `harmonization_outputs/validation_summary.csv`, `harmonization_outputs/validation_report.csv`,
  `harmonization_outputs/top_review_items_with_source_evidence.md`,
  `harmonization_outputs/expanded_reviewer_examples_draft.md`,
  `scripts/config/harmonization_config.yaml`, `scripts/lib/normalize.py`,
  `scripts/extract_harmonized_clinical.py`, `scripts/validate_extractions.py`,
  `scripts/build_exclusion_and_order_checks.py`, all per-trial extractors in
  `scripts/extractors/`

---

## 1. Executive summary

| Bucket | Items | Action |
|---|---|---|
| **Confirmed; verify only (no code change)** | #1 pfs_bin 120-day, #2 bor_bin 120-day SD landmark, #3 10026 CRm/CRi → R, #4 E4412 `round()` | Run **verification queries** against `harmonization_config.yaml`, `scripts/lib/normalize.py`, `scripts/extractors/e4412.py`, and `provenance_long.csv` to confirm in-effect. Optional: drop "pending final clinical confirmation" wording from provenance notes for #1/#2 and from `final_handoff_report.md` § 3/§5. |
| **Source-fidelity verification (no rule change)** | #6 9204 age = 64 (CD5Z7O5) | Verify the pipeline emits **64** (source-backed). The Edgar value 68 becomes a `template_anomalies.csv` entry. |
| **Implementation required — small surgical edits** | #7 S1400I `age` integer-fallback, #8 E4412 `Unevaluable [...]` → `other`, #9 9204 race `Other` → `Other`, #10 9204 `Day_8` → `first_sample_post_treatment` | Each is a 1–3 line YAML / extractor change. Validation impact is well-bounded (5 cells closed, ~561 new "expected non-matches" on S1400I `age`, plus a handful of reviewer-chosen pipeline-vs-Edgar disagreements that go to `template_anomalies.csv`). |
| **Implementation required — schema change** | #5 10104 BOR/BOR.binary → `clinical_benefit`/`clinical_benefit.binary` + keep source-backed values | **Multi-file schema rename.** Touches the orchestrator schema constant, the YAML normalization key, the BOR-binary derivation helper, **10 extractors**, `validate_extractions.py`, **5 report-builder scripts**, all reviewer artifacts, and the 9-trial template comparison path. Treated as its own section (§ 3). |
| **Needs clarification before implementing** | Scope of #5 rename (global vs 10104-only); capitalization (`other` vs `Other`) for #8; whether S1400I `age` confidence should rise above the 0.80 threshold or the threshold itself drop for that trial; whether to add `template_anomalies.csv` rows for #6, #9, #10 reviewer-chosen pipeline values that diverge from Edgar | See § 2 "risks/ambiguities" rows; do not start implementation until resolved. |

**One-line state for each item:**

| # | item | reviewer decision | current state | code change? |
|---|---|---|---|---|
| 1 | pfs_bin 120-day landmark | Confirmed | ✓ Already in code (`derive_pfs_bin`); 2,000 provenance rows = `derived_pfs_bin_120d` | No — verify only |
| 2 | bor_bin 120-day SD landmark | Confirmed | ✓ Already in code (`derive_bor_bin`); 2,000 provenance rows = `derived_bor_bin_120d` | No — verify only |
| 3 | 10026 CRm/CRi → R | Confirmed | ✓ Already in YAML `value_normalizations.BOR.binary.R` | No — verify only |
| 4 | E4412 `round()` time conversion | Confirmed (keep `round`) | ✓ Already `round(v × 30.4375)` at `scripts/extractors/e4412.py:62` | No — verify only |
| 5 | 10104 BOR → `clinical_benefit`, BOR.binary → `clinical_benefit.binary`, source-backed | Implement schema rename; keep source values when Edgar disagrees | Today: `BOR` and `BOR.binary` are project-wide columns; 10104 already source-backed but 26 cells flag as Edgar mismatches | **Yes** — see § 3 |
| 6 | 9204 age (CD5Z7O5) source = 64 | Confirmed | Pipeline already emits 64 (verified in `validation_report.csv`) | No — verify + add to `template_anomalies.csv` |
| 7 | S1400I `age` use integer | Implement | Today: extractor emits integer with confidence 0.55, falling below threshold 0.80 → all 561 cells NA + flagged | Yes — bump confidence (and / or threshold) |
| 8 | E4412 `Unevaluable [...]` → Other | Implement | Today: no rule; 16 cells preserved verbatim, diverge from Edgar's `other` | Yes — add `contains: "Unevaluable"` rule |
| 9 | 9204 race `Other` → `Other` | Implement; **do not** map to `unk` | Today: no rule for `Other`; 2 cells emit NA + flag | Yes — add `Other → Other` (capital O) to `value_normalizations.race` (or to 9204 trial value_map) |
| 10 | 9204 `Day_8` → `first_sample_post_treatment` | Implement (with underscore) | Today: YAML maps `Day_8 → Baseline`; 2 cells diverge from Edgar's `C2` | Yes — change one YAML entry |

---

## 2. Item-by-item implementation plan

### Item 1 — pfs_bin 120-day landmark

- **Rule / item.** `pfs_bin = 1 iff pfs_time ≥ 120; = 0 iff pfs_time < 120 AND pfs_stat == 1; = NaN iff pfs_time < 120 AND pfs_stat == 0`.
- **Reviewer decision.** Confirmed — current rule is correct.
- **Current implementation status.** Implemented in `scripts/lib/normalize.py::derive_pfs_bin` (lines 132–171). Landmark parameterized in YAML at `derived_rules.pfs_bin_landmark_days: 120` (line 43). Confirmed in `harmonization_outputs/provenance_long.csv`: every one of the 2,000 `pfs_bin` cells carries `extraction_method = derived_pfs_bin_120d`.
- **Likely files to edit.** None.
- **Exact proposed change.** None. Optional: drop the "pending final clinical confirmation" suffix from `scripts/lib/normalize.py` notes (lines 150–152, 161–164, 167–170) and from the YAML `derived_rules.status_note` (line 44). Optional: remove the stale "NOT committed / 183-day hypothesis" wording in `scripts/build_final_handoff.py` (lines 168–170, 222–223, 293).
- **Expected affected outputs.** None (verification). Optional wording changes do not change cell values.
- **Validation check after change.**
  ```
  awk -F',' 'NR==1{for(i=1;i<=NF;i++) if($i=="harmonized_field") hf=i; next} $hf=="pfs_bin"' \
      harmonization_outputs/provenance_long.csv | wc -l   # expect 2000
  ```
  Confirm `validation_summary.csv` pfs_bin column rates unchanged (ABTC1603 0.980, 10104 0.967, CIMAC-gu16257 0.990; all others 1.000).
- **Risks / ambiguities.** None. The optional `final_handoff_report.md` cleanup belongs in `scripts/build_final_handoff.py`, not a manual edit to the generated `.md`.

### Item 2 — bor_bin 120-day SD landmark

- **Rule / item.** `bor_bin = 1 iff BOR.binary='R' OR (BOR.binary='SD' AND pfs_time ≥ 120); = 0 iff 'NR' OR ('SD' AND pfs_time < 120); = NaN otherwise`.
- **Reviewer decision.** Confirmed.
- **Current implementation status.** `scripts/lib/normalize.py::derive_bor_bin` (lines 90–129); landmark `derived_rules.bor_bin_landmark_days: 120` (YAML line 42). 2,000 provenance cells = `derived_bor_bin_120d`.
- **Likely files to edit.** None (same as Item 1).
- **Exact proposed change.** None. Optional wording cleanup as in Item 1.
- **Expected affected outputs.** None.
- **Validation check.** As Item 1, substituting `bor_bin`. Confirm `validation_summary.csv` rates: 10026 0.832, 10104 0.967, all others 1.000.
- **Risks / ambiguities.** None.
- **Coupled item.** This rule depends on `BOR.binary`. If Item 5 renames `BOR.binary` → `clinical_benefit.binary` globally, `derive_bor_bin` will need to **read the renamed field** (signature can stay; the calling code in every extractor must pass the renamed value). See § 3.

### Item 3 — 10026 CRm / CRi → R

- **Rule / item.** Map `CRm` (Bone Marrow CR), `CRi` (Morphologic CR w/ Incomplete Blood Count Recovery), `CR with MRD-`, `CR with incomplete count recovery` to `BOR.binary = R`.
- **Reviewer decision.** Confirmed.
- **Current implementation status.** Already in YAML `value_normalizations.BOR.binary.R` (lines 732–740). 36 rows currently emit `R` where Edgar preserved the literal short codes; this is the D9 trade-off and is the **chosen** branch.
- **Likely files to edit.** None.
- **Exact proposed change.** None for the rule itself. **Recommended supplementary action:** add the 54 `BOR.binary` rows (`CRm` × 25, `CRi` × 11, `-` × 2, blank/`MLFS` × 16) and 36 `bor_bin` rows to `template_anomalies.csv` so the residual mismatches are explicitly documented. This is currently generated by `scripts/generate_review_report.py`; the additions should go there, not by manually editing `template_anomalies.csv`.
- **Expected affected outputs.** `template_anomalies.csv` row count grows by ≤90. `validation_summary.csv` values unchanged.
- **Validation check.**
  ```
  python -c "import pandas as pd; df=pd.read_csv('harmonization_outputs/provenance_long.csv'); \
    print(df[(df.trial=='10026') & (df.harmonized_field=='BOR.binary') & (df.value=='R')].shape)"
  ```
  Expect ≥36 rows (the CRm/CRi rows).
- **Risks / ambiguities.** If Item 5's BOR.binary rename is global, the YAML key `value_normalizations.BOR.binary` must be renamed to `value_normalizations.clinical_benefit.binary` (or kept under `BOR.binary` as the "internal label" — see § 3 design question).

### Item 4 — E4412 time conversion

- **Rule / item.** `os_time`/`pfs_time` for E4412 = `round(months × 30.4375)` (source `_wk` columns actually encode months).
- **Reviewer decision.** Use `round`, not `int` truncation. Keep current behavior.
- **Current implementation status.** `scripts/extractors/e4412.py` line 62: `days = round(v * float(time_conv.get(target, 7.0))) if v is not None else None`. ✓ Already `round`.
- **Likely files to edit.** None.
- **Exact proposed change.** None. **Important:** decision item D10 in `harmonization_outputs/top_review_items_with_source_evidence.md` (and the slide draft) proposed `round() → int()`. The reviewer **rejected** that proposal. Update the draft slide / decision memo to mark D10 "rejected; current `round()` retained" — but only in `expanded_reviewer_examples_draft.md` / `top_review_items_with_source_evidence.md` (these are reviewer materials, not generated outputs; however, the `top_review_items` file was previously regenerated, so the source-of-truth update should be in `scripts/build_review_checklist.py` or in a new draft revision).
- **Expected affected outputs.** None.
- **Validation check.** Confirm 19 e4412 time mismatches remain (`os_time` 8 + `pfs_time` 11) — these are **expected residuals** since Edgar applied `int()` truncation. Add to `template_anomalies.csv` if reviewer wants the divergence documented.
- **Risks / ambiguities.** None.

### Item 5 — 10104 BOR / BOR.binary rename + source-fidelity

See **§ 3 Special schema-change section** below.

### Item 6 — 9204 age

- **Rule / item.** Pipeline emits patient CD5Z7O5 age = 64 from `Age at Enrollment`. Edgar's template carries 68 (from the nivolumab file's `Age at Registration` column for the same patient).
- **Reviewer decision.** Source value 64 is correct. (Keep pipeline value.)
- **Current implementation status.** Verified in `validation_report.csv`: 1 row, `template=68, pipeline=64`. Pipeline behavior is correct.
- **Likely files to edit.** None for the rule. **Add a `template_anomalies.csv` entry** for CD5Z7O5 age via `scripts/generate_review_report.py`.
- **Exact proposed change.** None for the harmonization. Optional anomaly-doc entry.
- **Expected affected outputs.** `validation_summary.csv` CIMAC-9204 age stays at 0.985. `template_anomalies.csv` row count +1.
- **Validation check.**
  ```
  python -c "import pandas as pd; \
    df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
    print(df[(df.trial=='CIMAC-9204') & (df.cimac_part_id=='CD5Z7O5')][['cimac_part_id','age']])"
  ```
  Expect `age = 64`.
- **Risks / ambiguities.** Confirm that the 1 mismatch in `validation_summary` is CD5Z7O5 (not some other patient). One read of the validation report is sufficient.

### Item 7 — S1400I age (use integer source)

- **Rule / item.** Use source `age_num` (integer, age at enrollment) as the harmonized `age` for CIMAC-s1400i. The 561-row template carries decimal per-sample ages that were truncated upstream at the CIDC step and cannot be recovered.
- **Reviewer decision.** Use the integer source value.
- **Current implementation status.** `scripts/extractors/s1400i.py` lines 109–122: the extractor already extracts the integer source value, but with `confidence = 0.55`. The per-field threshold for `age` is **0.80** (`harmonization_config.yaml` line 75). Therefore every cell falls below threshold and is written as NA + flagged. **No value reaches `harmonized_11trials.csv`.**
- **Likely files to edit.**
  - `scripts/extractors/s1400i.py` lines 109–122: bump confidence; rewrite `extraction_method` and `notes` to reflect "reviewer-approved integer substitute".
  - Optionally `scripts/config/harmonization_config.yaml` — but a threshold drop is the **less preferred** path because it affects all trials.
- **Exact proposed change** (recommended path — confidence bump in extractor, no threshold change):
  ```python
  # scripts/extractors/s1400i.py — replace lines 109–122
  if harmonized == "age":
      try:
          v = float(raw_norm) if raw_norm not in (None, ".") else None
      except (TypeError, ValueError):
          v = None
      yield self.cell(anchor, "age", v, 0.95 if v is not None else 0.0,
                      src_file, src_col, src_idx, "age_at_enrollment_integer_substitute",
                      notes=(
                          "Reviewer-approved substitute (2026-05-20): integer age_num at "
                          "enrollment used in place of template decimal age. Decimal age "
                          "was truncated upstream at CIDC step and is not recoverable from "
                          "any S1400I source file."
                      ))
      continue
  ```
- **Expected affected outputs.**
  - `harmonized_11trials.csv`: 561 S1400I rows gain integer `age`.
  - `flagged_for_review.csv`: 561 fewer rows.
  - `provenance_long.csv`: 561 cells change `extraction_method` to `age_at_enrollment_integer_substitute` and confidence to 0.95.
  - `validation_summary.csv`: **CIMAC-s1400i age match rate will stay at 0.000** because the template's per-sample decimal ages differ from the integer enrollment age. The 561 mismatches reclassify from `missing_in_reproduced` → `numeric_diff` in `validation_report.csv`.
  - `template_anomalies.csv` — add 561 entries (or a single explanatory note keyed to the patient set) saying "Edgar's decimal age is not recoverable from source; integer enrollment age substituted per reviewer decision 2026-05-20."
- **Validation check.**
  ```
  python -c "import pandas as pd; \
    df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
    s=df[df.trial=='CIMAC-s1400i']; print(s['age'].notna().sum(), s['age'].dtype)"
  # expect 561 non-null, integer-ish dtype
  ```
- **Risks / ambiguities.**
  1. **Decimal-vs-integer mismatches** will still register as 561 numeric_diff entries in `validation_report.csv` — that is **expected and approved**. Confirm reviewer understands the validation rate stays at 0.000 against the template even though the pipeline is now reviewer-correct.
  2. Alternative: lower the `confidence_thresholds.per_field.age` to 0.50, which would also let the cell flow through. **Not recommended** — it loosens the threshold for every trial.
  3. The 0.55 → 0.95 confidence bump is a reviewer-approved override of the pipeline's "no silent guessing" policy. The note string makes that explicit.

### Item 8 — E4412 `Unevaluable [<reason>]` → Other

- **Rule / item.** Map bracketed source values like `Unevaluable [Scan obtained <6wks(criteria for SD)]`, `Unevaluable [No follow-up dx assessment; patient death]`, `Unevaluable [NPT before first dx assessment follow-up]`, `Unevaluable [pt went off tx after C1]`, `Unevaluable [Pt ended tx after C1]` (8 unique strings, 8 rows for `BOR` + 8 rows for `BOR.binary` = 16 cells) to `Other` in `BOR` **and** `BOR.binary`.
- **Reviewer decision.** Map to **Other**.
- **Current implementation status.** No `contains` rule. The global BOR.binary `other` bucket lists `UE, Unevaluable, NE, Not Applicable` (exact matches only); bracketed labels don't match. Currently the source string is preserved verbatim in BOR; `BOR.binary` falls through to NaN.
- **Capitalization check.** The current YAML uses **lowercase `other`** as the BOR.binary bucket label (line 749). Reviewer wrote **`Other`** (capital O). This is a small convention question — see "Risks/ambiguities" below.
- **Likely files to edit.**
  - `scripts/config/harmonization_config.yaml` — add `contains: "Unevaluable"` rule to `value_normalizations.BOR` (currently absent) and update `value_normalizations.BOR.binary.other` list to ensure the contains-rule fires.
- **Exact proposed change.**
  ```yaml
  # value_normalizations:
  #   BOR:
  #     - {match: "Unevaluable", value: "Other", kind: contains, confidence: 0.90,
  #        note: "E4412 bracketed Unevaluable labels → Other (reviewer 2026-05-20)"}
  #   BOR.binary:
  #     R: [...]
  #     SD: [...]
  #     NR: [...]
  #     other: [..., contains:Unevaluable]   # contains-rule equivalent
  ```
  Implementation note: `BOR` currently has **no entries** in `value_normalizations`. Adding one is structurally consistent with the existing `race`/`sex`/`os_stat`/`pfs_stat`/`BOR.binary` block (a list of `{match, value, kind, confidence, note}` dicts). The E4412 extractor sends raw BOR through `value_map_trial` first (current E4412 trial-level value_map has `Unevaluable → ` not defined); the `value_normalizations.BOR` rule fires only if no trial-level map matched. **For the BOR.binary side**, the bracketed string passes the `derive_bor_binary` lookup which is exact-string against the bucket lists — those lists already include `Unevaluable` (exact), but not bracketed forms. Cleanest fix is to extend `derive_bor_binary` to also try `contains`-style matching, **or** add the global BOR value-normalization first so the BOR column is canonicalized to `Other` before binarization.
- **Expected affected outputs.**
  - `harmonized_11trials.csv`: 8 e4412 BOR cells change to `Other` (or `other`); 8 BOR.binary cells change from NaN to `Other`/`other`.
  - `validation_summary.csv`: CIMAC-e4412 BOR rate moves from 0.952 (159/167) toward higher if Edgar's value is also `other`; same for BOR.binary. If Edgar's value is `other` (lowercase) and we emit `Other` (uppercase), the 8 mismatches **remain** as `case_diff` rather than going to perfect — so capitalization matters.
- **Validation check.** Spot-check the 8 affected cells in `validation_report.csv` after rerun; expect their `mismatch_kind` to flip from `value_diff` to either `match` (if capitalization aligns with Edgar) or `case_diff` (if not). Then either accept and document as template_anomalies or unify capitalization.
- **Risks / ambiguities.**
  1. **Capitalization.** Reviewer wrote `Other`; existing convention uses lowercase `other`. Confirm whether the canonical bucket is being **renamed to `Other` (case change project-wide, breaking change to BOR.binary keys)** or whether the reviewer simply meant "the existing `other` category" colloquially. **Recommendation: ask before implementing.**
  2. The contains-rule in `normalize.py` already exists (`kind: contains` matches when `m.lower() in s.lower()`); however, `derive_bor_binary` uses exact-string matching against the bucket lists. To make `Unevaluable [...]` resolve to `other`, the cleanest fix is to **canonicalize BOR first** via `value_normalizations.BOR` (so `BOR = "Other"`) and let the binarization map `"Other" → other` via a new exact-match entry, or extend `derive_bor_binary` to support contains-style matching.
  3. Coupled to Item 5 if the column is renamed: the YAML key `value_normalizations.BOR.binary` may need to be `clinical_benefit.binary` or stay as `BOR.binary` (internal label).

### Item 9 — 9204 race `Other` → `Other`

- **Rule / item.** When the source race value is `Other` (capital O — confirmed in `9204-clinical/demographics_dose_level.ipilimumab_2024-05-01.csv` → patient CD5Z9AG), emit harmonized `race = Other`. Do **not** map to `unk` (which was the prior D14 proposal).
- **Reviewer decision.** Map `Other → Other`. Explicitly reject the `Other → unk` proposal.
- **Current implementation status.** No rule; the value falls through with confidence 0.5 → below threshold 0.70 → NA + flagged. Edgar's template has `unk` for these 2 cells.
- **Likely files to edit.**
  - `scripts/config/harmonization_config.yaml` — add one entry to `value_normalizations.race`. Trial-specific override is also possible under `9204-clinical.value_maps.race`, but global is cleaner (the rule is reasonable for any trial).
- **Exact proposed change.**
  ```yaml
  # value_normalizations:
  #   race:
  #     - {match: "Other", value: "Other", kind: iexact, confidence: 0.95,
  #        note: "9204 source 'Other' preserved verbatim per reviewer 2026-05-20"}
  ```
  Insert **above** the `not reported → unk` rule so it takes precedence; the rule list is first-match-wins.
- **Expected affected outputs.**
  - `harmonized_11trials.csv`: 2 9204 rows change from NaN to `Other`.
  - `validation_summary.csv`: CIMAC-9204 race stays at **0.969** (the 2 mismatches change from `missing_in_reproduced` to `value_diff` — pipeline `Other` vs template `unk`). The match rate does not improve because the reviewer has explicitly chosen a value that disagrees with Edgar.
  - `flagged_for_review.csv`: 2 fewer rows.
  - `template_anomalies.csv` — recommended new entries (2 rows) saying "9204 source 'Other' preserved per reviewer; Edgar's `unk` is a template choice we are not adopting."
- **Validation check.**
  ```
  python -c "import pandas as pd; df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
    print(df[(df.trial=='CIMAC-9204') & (df.race=='Other')][['cimac_part_id','race']])"
  # expect CD5Z9AG and 1 other
  ```
- **Risks / ambiguities.**
  1. **Capital `Other` vs lowercase `other`.** This race rule writes capital `Other`; the BOR.binary `other` bucket uses lowercase. The reviewer was explicit ("map Other to Other"), so capitalization is preserved. Flag the convention divergence.
  2. The new value `Other` is not currently a recognized harmonized race value. Downstream code that one-hot-encodes race should be aware; not a pipeline concern.

### Item 10 — 9204 `Collection_Event_alt`: `Day_8` → `first_sample_post_treatment`

- **Rule / item.** Map source `Collection_Event = Day_8` to harmonized `Collection_Event_alt = first_sample_post_treatment` (underscored, per James' clarification).
- **Reviewer decision.** Use the string `first_sample_post_treatment` **with underscores** (not `first_sample_post-treatment`, not `C2`).
- **Current implementation status.** YAML `9204-clinical.collection_event_alt_map.Day_8: Baseline` (line 582). 2 rows currently get `Baseline`; Edgar carries `C2`. The reviewer overrides both.
- **Likely files to edit.**
  - `scripts/config/harmonization_config.yaml` line 582.
- **Exact proposed change.**
  ```yaml
  # scripts/config/harmonization_config.yaml — under 9204-clinical:
  #   collection_event_alt_map:
  #     ...
  #     "Day_8": "first_sample_post_treatment"   # was: "Baseline"; per reviewer 2026-05-20
  ```
- **Expected affected outputs.**
  - `harmonized_11trials.csv`: 2 9204 rows change from `Baseline` to `first_sample_post_treatment`.
  - `validation_summary.csv`: CIMAC-9204 Collection_Event_alt stays at **0.969** (2 mismatches now `value_diff` pipeline `first_sample_post_treatment` vs template `C2`).
  - `template_anomalies.csv` — recommended new entries (2 rows).
- **Validation check.**
  ```
  python -c "import pandas as pd; df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
    print(df[(df.trial=='CIMAC-9204') & (df.Collection_Event=='Day_8')] \
            [['cimac_part_id','Collection_Event','Collection_Event_alt']])"
  # expect both rows show first_sample_post_treatment
  ```
- **Risks / ambiguities.** None. The string is preserved verbatim per James' clarification.

---

## 3. Special schema-change section — BOR → clinical_benefit, BOR.binary → clinical_benefit.binary

### 3.1 Scope clarification (**critical — confirm before implementation**)

The reviewer slide says "For 10104 BOR / BOR.binary: rename BOR to clinical_benefit, rename BOR.binary to clinical_benefit.binary, do not add alias columns, intended output field names should replace BOR and BOR.binary." James' clarification reinforces this with "the intended output field names should replace BOR and BOR.binary."

Two readings:

| Reading | Description | Implication |
|---|---|---|
| **(A) Global rename** (recommended) | Rename the harmonized columns `BOR` → `clinical_benefit` and `BOR.binary` → `clinical_benefit.binary` for **every trial** in the harmonized output schema | Single consistent schema; the 10104 source-fidelity rule applies because pipeline already emits source-backed values; all 9 + 2 trials affected |
| **(B) 10104-only rename** | Only the 10104 trial's column values are emitted under the new names; other trials still use BOR / BOR.binary | Output has **two different column families** depending on `trial`; this is unusual and almost certainly **not what was intended** |

**Strongly recommended: (A) Global rename.** Reasons:
- A single harmonized CSV cannot have a column whose name depends on the row's `trial` value.
- The reviewer wrote "replace BOR and BOR.binary" — replacement is global.
- All current consumers (`validate_extractions.py`, all 5 report builders, all reviewer artifacts) read by column name; one consistent rename is cleaner than per-trial branching.
- The semantic re-framing — "this is the clinical-benefit endpoint, not a RECIST best-response code" — is **trial-agnostic** and matches what the column actually carries (e.g., 10021 uses `Clin-Ben`/`No C-B`, S1400I uses RECIST short codes that feed into the same binary, all derivations are about clinical benefit).

**Required clarification before implementing:** confirm (A) vs (B). The plan below assumes **(A) Global rename**.

### 3.2 Files affected (verified by grep of the repo)

| Layer | File(s) | Nature of change | Lines |
|---|---|---|---|
| **Schema constant** | `scripts/extract_harmonized_clinical.py` | `TEMPLATE_COLUMNS` list: replace `"BOR"` → `"clinical_benefit"`, `"BOR.binary"` → `"clinical_benefit.binary"` | lines 36–40 |
| **Config — confidence thresholds** | `scripts/config/harmonization_config.yaml` | Rename two keys: `confidence_thresholds.per_field.BOR` → `clinical_benefit`; `BOR.binary` → `clinical_benefit.binary` | lines 81, 84 |
| **Config — value_normalizations** | `scripts/config/harmonization_config.yaml` | Rename top-level keys: `value_normalizations.BOR` (if present) → `clinical_benefit`; `value_normalizations.BOR.binary` → `clinical_benefit.binary` | lines 717–750 |
| **Config — per-trial column_map** | `scripts/config/harmonization_config.yaml` | Every per-trial `column_map` entry whose RHS is `BOR` or `BOR.binary` should be updated to `clinical_benefit` / `clinical_benefit.binary`. Affected trials: EAY131-Z1D (line 151), S1400I (184), 10026 (334), GU16-257 (293), 10104 (389, 395), 10021 (433), E4412 (479), 9204 (561, 563), 10013 (604), 14C0059G (643). Also the `value_maps` blocks (E4412 line 509, 10021 line 449). | many lines |
| **Config — trial_constants** | `scripts/config/harmonization_config.yaml` | ABTC1603 line 258: `"BOR.binary": "other"` → `"clinical_benefit.binary": "other"` | line 258 |
| **Derivation helpers** | `scripts/lib/normalize.py` | `derive_bor_binary` and `derive_bor_bin` reference the field name only in their docstrings and notes. Function signatures unaffected. Internal literals `'R'/'NR'/'SD'/'other'` unaffected (these are values, not column names). | docstrings only |
| **BaseExtractor** | `scripts/lib/extractor_base.py` | Method `derive_BOR_binary` reads `self.value_norms.get("BOR.binary")` — change to `get("clinical_benefit.binary")` to match the renamed YAML key | lines 94–95 |
| **Per-trial extractors (10 files)** | `scripts/extractors/{abtc1603,e4412,eay131_z1d,gu16_257,nci_10013,nci_10021,nci_10026,nci_10104,nci_9204,nih_14c0059g,s1400i}.py` | Every `yield self.cell(..., "BOR", ...)` and `yield self.cell(..., "BOR.binary", ...)` becomes `"clinical_benefit"` / `"clinical_benefit.binary"`. Local Python variable names `cur_bor`, `bin_val` can stay (they're internal) but tracking variable named harmonized_field should be updated. Method name `derive_BOR_binary` in `extractor_base.py` may stay (internal) or be renamed to `derive_clinical_benefit_binary` for clarity. | grep shows hits in all extractors |
| **Validation** | `scripts/validate_extractions.py` | Edgar's template still has columns named `BOR` and `BOR.binary`. After the rename, the pipeline emits `clinical_benefit` / `clinical_benefit.binary`. Validation must **map template column names to pipeline column names** before comparison. Recommended: add a constant `TEMPLATE_TO_PIPELINE = {"BOR": "clinical_benefit", "BOR.binary": "clinical_benefit.binary"}` near `KEY_COLS`, and rename the template DataFrame's columns immediately after `pd.read_csv` (line 55) using this map. After that one-line rename, the rest of the script works unchanged. | line 55 + new mapping constant near line 25 |
| **Report builders** | `scripts/build_final_handoff.py`, `scripts/build_review_checklist.py`, `scripts/build_nonperfect_match_review.py`, `scripts/generate_review_report.py` | Many string literals reference `BOR`/`BOR.binary` in markdown body text and in column-set filters. Each string-match must be updated. Estimate: ~25 string updates across 4 files. | see grep output |
| **Exclusion check** | `scripts/build_exclusion_and_order_checks.py` | Does **not** reference BOR/BOR.binary directly; uses the `trial` column and BACCI scans. Unaffected by the rename. | n/a |
| **Reviewer artifacts** | `harmonization_outputs/top_review_items_with_source_evidence.md`, `harmonization_outputs/expanded_reviewer_examples_draft.md`, `harmonization_outputs/final_handoff_report.md`, `harmonization_outputs/reviewer_intro_summary_tables.md/.csv`, `harmonization_outputs/nonperfect_match_review.md` | These are markdown/CSV. They will be regenerated by the report builders after the rename. **Do not manually edit** them — let the next pipeline run regenerate them with the new column names (the source-of-truth update is in the build scripts). | n/a (auto-regenerated) |
| **PROJECT_HANDOFF doc** | `PROJECT_HANDOFF_CURRENT_STATE.md` | Has multiple references to BOR/BOR.binary in narrative text. Will not be auto-regenerated. Update in a separate manual edit pass **after** the rename, or leave as-is and add a one-line "Renamed BOR/BOR.binary → clinical_benefit/clinical_benefit.binary on 2026-05-20" note at the top. | manual touch-up |
| **README.txt** | `README.txt` | Contains BOR/BOR.binary in narrative; auto-regenerated? No — it's static. Update narrative. | manual touch-up |

### 3.3 Validation against Edgar's 9-trial template after the rename

Edgar's template (`cross_trial_analysis_egk_april30_meta_9trials.csv`) still uses column names `BOR` and `BOR.binary` (verified by header inspection). The pipeline will emit `clinical_benefit` / `clinical_benefit.binary`.

**Recommended approach: schema-mapping in `validate_extractions.py` only.** Do not rename Edgar's template file. Do not maintain alias columns in the pipeline output. The mapping is one-directional and one-place:

```python
# scripts/validate_extractions.py — near KEY_COLS (~line 25):
TEMPLATE_TO_PIPELINE = {
    "BOR": "clinical_benefit",
    "BOR.binary": "clinical_benefit.binary",
}

# scripts/validate_extractions.py — after `tpl = pd.read_csv(args.template, ...)` (~line 55):
tpl = tpl.rename(columns=TEMPLATE_TO_PIPELINE)
```

Effect: validation compares Edgar's `BOR` column (renamed in-memory to `clinical_benefit`) against the pipeline's `clinical_benefit` column. The `validation_report.csv` `column` value will read `clinical_benefit` / `clinical_benefit.binary`. The `validation_summary.csv` aggregate will report the renamed fields. Mismatch counts and rates **do not** change just from the rename — but **the 10104 source-fidelity rule** means the 10104 BOR template-anomaly rows (R005–R009, ~9 BOR + 17 BOR.binary cells) **stay as mismatches and must be added to `template_anomalies.csv`** rather than the pipeline being changed to match Edgar.

### 3.4 10104 source-fidelity (sub-decision of Item 5)

The "do not use Edgar's template to override the source-backed value" instruction for 10104 codifies what the pipeline already does (the 10104 extractor reads `best_response` from the source response file and emits it verbatim into BOR; the global binarization map then derives BOR.binary). **No code change required for source-fidelity per se**, but:

- The 26 10104 cells (`BOR` 9 + `BOR.binary` 17) that disagree with Edgar are now reviewer-approved as pipeline-correct.
- Each should be added to `template_anomalies.csv` (via `scripts/generate_review_report.py`) with a note like "10104 reviewer 2026-05-20: source value retained; Edgar appears to encode a different category".
- The `top_review_items_with_source_evidence.md` decision item **D12** ("add 7 R005–R007 rows to `template_anomalies.csv`") is therefore **approved** as part of Item 5.

### 3.5 Aliases / backward compatibility

Reviewer explicitly said **do not add alias columns**. The plan honors this. No `BOR` / `BOR.binary` columns will remain in `harmonized_11trials.csv` or `harmonized_9trials_reproduced.csv` after the rename. Any downstream consumer that reads these columns by name must update.

If a temporary alias is unavoidable during the rollout (e.g., to keep an external dashboard alive for one day), it should be added at **read time in that consumer**, not in the pipeline output. Flag this if it comes up.

### 3.6 Risk register for Item 5

| risk | severity | mitigation |
|---|---|---|
| Edgar's template comparison silently breaks (validation report would show all cells as "missing_in_reproduced" because columns no longer line up) | High | Apply the `TEMPLATE_TO_PIPELINE` rename in `validate_extractions.py` in the same commit as the schema rename; verify by running validation and checking the BOR/BOR.binary mismatch count stays at 17 + 26 ≈ 43 cells (the same as today) — not zero (=accidental schema break) and not all cells (=mapping not applied) |
| Report builders silently drop BOR/BOR.binary references | Medium | grep `BOR\\|BOR\\.binary` over scripts/ after the rename — should return only intentional matches (e.g., Edgar's template column name in narrative text or in `template_anomalies.csv` context) |
| Downstream consumers (slide decks, external analyses) still expect BOR | Medium | Add a one-paragraph "renamed columns" note at the top of `PROJECT_HANDOFF_CURRENT_STATE.md` and `README.txt` in the same change-set |
| Internal variable names (`cur_bor`, `bin_val`) stay as BOR-named — confusing | Low | Acceptable for first pass; rename in a follow-up cleanup if reviewers prefer |
| YAML internal keys (`value_normalizations.BOR.binary.R`/`.NR`/`.SD`/`other`) — note that the **value buckets** are R/NR/SD/other, **not column names**, so no rename needed inside the buckets | Low | Verify after rename: `derive_bor_binary` still receives the `clinical_benefit.binary` value bucket and matches against R/NR/SD/other internally |
| ABTC1603 trial_constant `"BOR.binary": "other"` (YAML line 258) | Low | Rename to `"clinical_benefit.binary": "other"` |

---

## 4. Recommended implementation order

A. **Verify the four confirmed/no-change items (#1–#4).** Read-only queries against `provenance_long.csv`, `harmonization_config.yaml`, and `scripts/lib/normalize.py` / `scripts/extractors/e4412.py`. No code change. Expected outcome: each verification passes; record results.

B. **Low-risk YAML/normalization edits (#8, #9, #10).** Each is 1–3 lines in `harmonization_config.yaml`. Before editing, resolve the **capitalization question** for #8 (`other` vs `Other`). After editing:
  - Rerun the pipeline (`./scripts/run_full_harmonization.sh`).
  - Confirm `validation_summary.csv` deltas: e4412 BOR/BOR.binary rates **change** (toward higher if capitalization aligns with Edgar; flat with `case_diff` reclassification if not); 9204 race and Collection_Event_alt stay at 0.969 (reviewer-approved divergences from Edgar).
  - Confirm `exclusion_and_order_checks.txt` → `VERDICT: PASS`.

C. **S1400I integer age (#7).** Modify `scripts/extractors/s1400i.py` lines 109–122 only. Rerun pipeline. Confirm 561 S1400I `age` cells are now non-null and `validation_summary.csv` rate **stays 0.000** (expected — integer vs decimal). `flagged_for_review.csv` drops by 561.

D. **BOR / BOR.binary rename (#5)** — **single commit**:
  1. Edit `scripts/extract_harmonized_clinical.py` `TEMPLATE_COLUMNS`.
  2. Edit `scripts/config/harmonization_config.yaml` keys (thresholds, value_normalizations, per-trial column_maps, ABTC1603 trial_constants).
  3. Edit `scripts/lib/extractor_base.py` `derive_BOR_binary`'s lookup key.
  4. Edit each of 10 per-trial extractors: `yield self.cell(..., "BOR", ...)` → `"clinical_benefit"`; same for `BOR.binary`.
  5. Edit `scripts/validate_extractions.py`: add `TEMPLATE_TO_PIPELINE` constant + rename template columns at read time.
  6. Edit the 4 report builders for the string-literal updates.
  7. Add `template_anomalies.csv` entries for the 26 source-backed 10104 cells (via `scripts/generate_review_report.py`).
  8. Rerun pipeline; full audit per § 5.

E. **Rerun full pipeline** (`./scripts/run_full_harmonization.sh`).

F. **Audit outputs** per § 5 below.

G. **Document the rename** in `PROJECT_HANDOFF_CURRENT_STATE.md` and `README.txt`. Refresh `expanded_reviewer_examples_draft.md` if the reviewer wants the slide deck to reflect the new column names.

H. **(Optional after F.)** Drop "pending final clinical confirmation" wording per Items 1 and 2.

Order rationale: A/B/C are independent and low-risk; D is the high-risk schema change and should be done **after** B/C so that any breakage is unambiguously attributable to the rename. Skipping ahead to D risks compounding issues.

---

## 5. Post-implementation validation checklist

Run after each of B, C, and D (and again at the end):

```bash
cd /gpfs/gsfs12/users/nextgen2/james/data/CIMAC/harmonization
source .venv/bin/activate
./scripts/run_full_harmonization.sh                                   # full pipeline
tail -5 harmonization_outputs/exclusion_and_order_checks.txt          # → VERDICT: PASS
```

Then run these checks (read-only):

1. **VERDICT: PASS** in `harmonization_outputs/exclusion_and_order_checks.txt`.
2. **BACCI still excluded.**
   ```
   grep -c BACCI harmonization_outputs/harmonized_11trials.csv  # expect 0
   grep VERDICT harmonization_outputs/exclusion_and_order_checks.txt
   ```
3. **Row count and schema.**
   ```
   .venv/bin/python -c "import pandas as pd; \
     df = pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
     print(df.shape, sorted(df['trial'].unique())); print(list(df.columns))"
   # expect (2000, 19); 11 trials including the new names; column list includes
   # clinical_benefit and clinical_benefit.binary (after step D); no BOR / BOR.binary
   ```
4. **9-trial reproduction row-order preserved.**
   ```
   .venv/bin/python -c "import pandas as pd; \
     d=pd.read_csv('harmonization_outputs/row_order_diagnostics.csv'); \
     print(d['issue_type'].value_counts().to_dict())"
   # expect: {'summary': 1}
   ```
5. **Validation against Edgar's template still aligned (after rename).**
   ```
   .venv/bin/python -c "import pandas as pd; \
     v=pd.read_csv('harmonization_outputs/validation_summary.csv'); \
     print(v[v.column.isin(['clinical_benefit','clinical_benefit.binary'])][['trial','column','n_rows','n_match','match_rate']].to_string())"
   # expect 10104 clinical_benefit ≈ 0.958 (9 mismatches) and clinical_benefit.binary ≈ 0.920 (17)
   # if either is 0 or n_rows is wildly off, the template→pipeline column mapping in
   # validate_extractions.py is broken
   ```
6. **Spot-check Item 6 (9204 age):**
   ```
   .venv/bin/python -c "import pandas as pd; df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
     print(df[(df.trial=='CIMAC-9204') & (df.cimac_part_id=='CD5Z7O5')][['cimac_part_id','age']])"
   # expect age = 64
   ```
7. **Spot-check Item 7 (S1400I integer age):**
   ```
   .venv/bin/python -c "import pandas as pd; \
     df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
     s=df[df.trial=='CIMAC-s1400i']; print('non-null age:', s['age'].notna().sum())"
   # expect 561
   ```
8. **Spot-check Item 8 (E4412 Unevaluable):**
   ```
   .venv/bin/python -c "import pandas as pd; \
     df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
     e=df[df.trial=='CIMAC-e4412']; print(e['clinical_benefit'].value_counts(dropna=False).head(10))"
   # expect Other/other category present in 8 rows; no row labeled 'Unevaluable [...]'
   ```
9. **Spot-check Item 9 (9204 race Other) and Item 10 (Day_8):**
   ```
   .venv/bin/python -c "import pandas as pd; \
     df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
     n=df[df.trial=='CIMAC-9204']; print('races:', n['race'].value_counts(dropna=False).to_dict()); \
     print('CE_alt:', n.loc[n['Collection_Event']=='Day_8', ['cimac_part_id','Collection_Event','Collection_Event_alt']])"
   # expect race contains 'Other' (2 rows); Day_8 rows show 'first_sample_post_treatment'
   ```
10. **Spot-check Item 5 (10104 source-fidelity for CWWG289 and similar):**
    ```
    .venv/bin/python -c "import pandas as pd; \
      df=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
      r=df[(df.trial=='10104') & (df.cimac_part_id=='CWWG289')]; \
      print(r[['cimac_part_id','clinical_benefit','clinical_benefit.binary']])"
    # expect source-backed value (e.g., PD), not Edgar's value
    ```
11. **Report-builder integrity.** Confirm no `KeyError: 'BOR'` or similar in the pipeline log; check `final_handoff_report.md`, `nonperfect_match_review.md`, `review_priority_checklist.md` all regenerated and reference `clinical_benefit` (after step D).
12. **Provenance still complete.** Every cell of the harmonized output must trace back to a `provenance_long.csv` row.
    ```
    .venv/bin/python -c "import pandas as pd; \
      h=pd.read_csv('harmonization_outputs/harmonized_11trials.csv'); \
      p=pd.read_csv('harmonization_outputs/provenance_long.csv'); \
      print('harmonized non-null cells:', h.set_index(['trial','cimac_part_id','Cimac.id','Collection_Event']).notna().sum().sum()); \
      print('provenance rows for harmonized fields:', p[p.harmonized_field.isin(h.columns)].shape[0])"
    ```
13. **Match-rate deltas vs the pre-change baseline.** Save `validation_summary.csv` before step B and diff after step D to confirm the only changed (trial, column) cells are those reviewer decisions explicitly address.

---

## 6. Items requiring clarification before implementation

| Question | Item | Why it matters | Recommendation |
|---|---|---|---|
| Is the BOR/BOR.binary rename **global** or **10104-only**? | 5 | Determines whether the rename touches 20 files or only 10104's extractor + a few output columns. **Strongly favors global** per § 3.1. | Confirm with reviewer. Assume global until told otherwise. |
| Is the Unevaluable target value `Other` (capital O) or `other` (existing convention)? | 8 | Determines whether the 8 e4412 cells become a perfect match against Edgar or remain `case_diff` mismatches. | Recommended: lowercase `other` (matches existing convention; gets the cells to a perfect match if Edgar has `other`). Confirm. |
| Should the S1400I integer-age cells be added to `template_anomalies.csv`? | 7 | 561 cells will register as numeric_diff against Edgar's decimal age forever. Anomaly documentation makes the divergence explicit. | Recommended yes. |
| Should the 2 race rows and 2 Collection_Event_alt rows for 9204 be added to `template_anomalies.csv`? | 9, 10 | Reviewer explicitly chose pipeline values that disagree with Edgar. Document to avoid future confusion. | Recommended yes. |
| Should the 10104 ~26 source-fidelity cells (BOR + BOR.binary) be added to `template_anomalies.csv` as part of Item 5? | 5 (sub) | The "do not override source with Edgar" rule means these mismatches are permanent; documenting them is the standard P3 approach (D12). | Recommended yes. |
| Should "pending final clinical confirmation" wording be dropped from provenance notes for #1 and #2? | 1, 2 | Cosmetic. Reviewer confirmed both rules. | Recommended yes, but separate cleanup pass (not blocking). |
| Do we also need a downstream slide-deck update for the renamed columns? | 5 (downstream) | The expanded reviewer draft and the (not-yet-created) `.pptx` will need column names updated. | Yes; do after step D. |

---

## 7. Sanity check on existing reviewer artifacts

These are flagged for refresh **after** the changes land (they are auto-regenerated by the build scripts; no manual edits needed):

- `harmonization_outputs/expanded_reviewer_examples_draft.md` — references `BOR` / `BOR.binary` throughout; will need to switch to `clinical_benefit` / `clinical_benefit.binary` after Item 5. Also: the draft's 120-day `bor_bin` slide still uses the old 10026 CBUPOJV example (per § 5 / § 8 of `PROJECT_HANDOFF_CURRENT_STATE.md`); the CCZRAUC / CCZRY9C s1400i pair swap is independent of this implementation plan.
- `harmonization_outputs/top_review_items_with_source_evidence.md` — D10 (`round() → int()`) was rejected. Mark "rejected; Item 4". D7, D8 are deferred (not in the current decision set).
- `harmonization_outputs/reviewer_intro_summary_tables.md` — Part 2's R3 rule and the "rules in code" table will need updates after the rename.
- `harmonization_outputs/final_handoff_report.md` — auto-regenerated, but the build script's narrative text (`scripts/build_final_handoff.py`) needs string updates.
- `README.txt`, `PROJECT_HANDOFF_CURRENT_STATE.md` — manual touch-up after rename.

---

## 8. Do not implement anything yet — open items list

1. Confirm scope of #5 rename: global (recommended) vs 10104-only.
2. Confirm capitalization for #8 Unevaluable target value.
3. Confirm whether reviewer-divergent cells go to `template_anomalies.csv` (items #6, #7, #9, #10, #5 source-fidelity).
4. Confirm whether the slide deck / expanded draft updates are part of this change-set or a follow-up.

Once these four are resolved, execute steps A → G in § 4 in order, with the full validation checklist in § 5 run between B/C/D and at the end.
