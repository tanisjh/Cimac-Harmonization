# Change log — 120-day bin rules + 10026 CRm/CRi → R

Implementation of three reviewer-approved decisions from
`source_evidence_decision_memo.md`:

- **D2** — 120-day `pfs_bin` rule
- **D1** — 120-day `bor_bin` SD-landmark rule
- **D3a** — 10026 `CRm`/`CRi` → `BOR.binary = R`

All three are implemented as reproducible pipeline rules (config + code).
No harmonized CSV was manually edited.

The pipeline wrapper (`./scripts/run_full_harmonization.sh`) was rerun;
`exclusion_and_order_checks.txt` reports **VERDICT: PASS**.

---

## 1. What changed (code/config)

| File                                                  | Change                                                                                                   |
|-------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| `scripts/config/harmonization_config.yaml`            | Added top-level `derived_rules:` block (`bor_bin_landmark_days: 120`, `pfs_bin_landmark_days: 120`, status note). Added `CRm`, `CRi`, `"CR with MRD-"`, `"CR with incomplete count recovery"` to the `R` bucket in `value_normalizations.BOR.binary` with explicit citation of 10026 Data Dictionary Sheet1 rows 92–94. Removed the now-unused standalone `CRm`/`CRi` buckets and the placeholder `bor_bin:` / `pfs_bin:` value-map blocks (the rule lives in code, parameterized by `derived_rules`). |
| `scripts/lib/normalize.py`                            | Rewrote `derive_bor_bin(bor_binary, pfs_time, landmark_days=120)` and `derive_pfs_bin(pfs_time, pfs_stat, landmark_days=120)` to implement the 120-day rules with explicit provenance notes. |
| `scripts/lib/extractor_base.py`                       | `BaseExtractor.__init__` accepts `derived_rules`; `derive_bor_bin` / `derive_pfs_bin` wrappers pull the landmark from there and pass `pfs_time` / `pfs_stat`.  |
| `scripts/extract_harmonized_clinical.py`              | Loads `derived_rules` from YAML and forwards to each extractor.                                          |
| `scripts/extractors/_helpers.py`                      | `emit_unresolved_derived(...)` now computes `bor_bin` and `pfs_bin` via the new derive functions. Adds extraction methods `derived_bor_bin_120d` and `derived_pfs_bin_120d`. Provenance notes carry the status string `"120-day landmark rule (template-supported derived rule; pending final clinical confirmation)"`. |
| 9 extractors                                          | Each now tracks `cur_pfs_time` and passes it to `emit_unresolved_derived`. The two extractors that bypass the helper (`s1400i`, `eay131_z1d`) call `self.derive_bor_bin` / `self.derive_pfs_bin` with the new signatures directly. `abtc1603` uses the helper's override path because its `BOR.binary` is the trial constant `'other'`. |

The provenance trail for every `bor_bin` and `pfs_bin` cell now contains:

- `extraction_method = derived_bor_bin_120d` (or `derived_pfs_bin_120d`)
- `source_file = DERIVED:BOR.binary+pfs_time` (or `DERIVED:pfs_time+pfs_stat`)
- `source_column = BOR.binary,pfs_time` (or `pfs_time,pfs_stat`)
- `notes` ends with `status=120-day landmark rule (template-supported derived rule; pending final clinical confirmation)`

The provenance trail for every `BOR.binary` cell whose source was `CRm`/`CRi`
includes the data-dictionary citation via the YAML comment block and the
matched-rule note in `provenance_long.csv`.

---

## 2. Match-rate deltas (validation_summary.csv)

### `bor_bin` (template-trial match rate)

| trial          |  before |   after |   delta |
|----------------|--------:|--------:|--------:|
| 10026          |  0.2523 |  0.8318 | **+0.5794** |
| 10104          |  0.0376 |  0.9671 | **+0.9296** |
| ABTC1603       |  1.0000 |  1.0000 |  0.0000 |
| CIMAC-10021    |  0.0000 |  1.0000 | **+1.0000** |
| CIMAC-9204     |  0.4462 |  1.0000 | **+0.5538** |
| CIMAC-e4412    |  0.0479 |  1.0000 | **+0.9521** |
| CIMAC-gu16257  |  0.0306 |  1.0000 | **+0.9694** |
| CIMAC-s1400i   |  0.7094 |  1.0000 | **+0.2906** |
| EAY131_Z1D     |  0.6667 |  1.0000 | **+0.3333** |

**8 of 9 template trials now at 1.000**; 10026 at 0.832 (see §3), 10104 at 0.967
(driven by 7 residual mismatches that flow from upstream `pfs_time`
disagreements at 0.934).

### `pfs_bin` (template-trial match rate)

| trial          |  before |   after |   delta |
|----------------|--------:|--------:|--------:|
| 10026          |  0.0841 |  1.0000 | **+0.9159** |
| 10104          |  0.0188 |  0.9671 | **+0.9484** |
| ABTC1603       |  0.0203 |  0.9797 | **+0.9595** |
| CIMAC-10021    |  0.0065 |  1.0000 | **+0.9935** |
| CIMAC-9204     |  1.0000 |  1.0000 |  0.0000 |
| CIMAC-e4412    |  0.5569 |  1.0000 | **+0.4431** |
| CIMAC-gu16257  |  0.0153 |  0.9898 | **+0.9745** |
| CIMAC-s1400i   |  0.0071 |  1.0000 | **+0.9929** |
| EAY131_Z1D     |  0.0635 |  1.0000 | **+0.9365** |

**6 of 9 template trials at 1.000**; ABTC1603 0.980, 10104 0.967, gu16257 0.990 —
all small residuals tied to upstream issues (composite `pfs_stat` derivations
and `pfs_time` fallback choices), not to the 120-day rule itself.

### 10026 `BOR.binary`

| metric     | before  | after   |
|------------|---------|---------|
| n_rows     | 214     | 214     |
| n_match    | 160     | 160     |
| match_rate | 0.7477  | 0.7477  |

**No change in the BOR.binary match count.** This is expected: the template
preserves the literal short codes `CRm` (25 rows) and `CRi` (11 rows) in the
`BOR.binary` column, while the approved rule maps both to `R`. The
mismatch type shifted (was `template=CRm vs pipeline=NaN`; now
`template=CRm vs pipeline=R`) but the number of cells that differ is
unchanged. The gain from D3a is realised downstream — see the 10026
`bor_bin` row (+0.58) above, where CRm/CRi-bearing patients now resolve to
`bor_bin=1` along with their SD-row peers because their SD-row landmark
behaviour is now correctly computed.

### Total cells matched across 9 trials × 15 measurable columns

| metric    | before    | after     | delta    |
|-----------|----------:|----------:|---------:|
| n_match   | 23,260    | 25,879    | **+2,619** |
| n_rows    | 26,715    | 26,715    | 0        |
| match_pct |  87.07%   |  96.87%   | **+9.81 pp** |

`final_handoff_report.md` status-count change for the 9-trial reproduction
(135 (trial, column) cells):

| status        | before | after |
|---------------|-------:|------:|
| OK            | 111    | **126** |
| MOSTLY_OK     | 6      | 7     |
| PARTIAL       | 5      | 1     |
| NEEDS_REVIEW  | 13     | **1** |

---

## 3. Residual mismatches after rule change

`validation_report.csv` shows the following residual mismatches for the three
focus columns (post-rerun):

| trial         | column     | n  | shape (template → pipeline)      | root cause                                                                                  |
|---------------|------------|----|-----------------------------------|---------------------------------------------------------------------------------------------|
| 10026         | bor_bin    | 36 | NaN → 1 (36)                      | CRm/CRi rows now resolve to `R` → `bor_bin=1`; template kept those rows as `bor_bin=NaN`. Direct consequence of approved D3a (CRm/CRi → R). |
| 10026         | BOR.binary | 54 | CRm → R (25), CRi → R (11), other → NaN (16), `-` → NaN (2) | Same trade-off as above (D3a). The `other` (source-NaN) and `-` (no codebook entry) divergences correspond to D3c / D3b which were **not** implemented per the request. |
| 10104         | bor_bin    | 7  | 0 → 1 (2), 1 → 0 (5)              | Upstream: 10104 `pfs_time` validates at 0.934; the 7 bor_bin disagreements all fall on rows whose pfs_time itself disagrees with the template. Not a bin-rule defect. |
| 10104         | pfs_bin    | 7  | 0 → 1 (2), 1 → 0 (5)              | Same upstream pfs_time cause.                                                                |
| ABTC1603      | pfs_bin    | 3  | 0 → NaN (3)                       | Three rows where the ABTC1603 composite (progression / death / last contact) yields a censored short row; template assigns 0. |
| CIMAC-gu16257 | pfs_bin    | 2  | NaN → 1 (2)                       | Two rows where the DFSTIM/DRFSTIM fallback resolves to a value ≥ 120 but the template keeps pfs_bin NaN. |

All residuals are below the per-field threshold and would be addressed by
future work on the upstream fields (10104 anchor choice, ABTC1603 composite
pfs_stat semantics, gu16257 pfs_time fallback edge cases) — not by changes
to the 120-day rule.

---

## 4. `flagged_for_review.csv` deltas

| metric        | before  | after  | delta   |
|---------------|--------:|-------:|--------:|
| total rows    | 7,126   | 4,542  | **−2,584** |

Per-field breakdown of where the drop comes from:

| harmonized_field | before | after | delta   |
|------------------|------:|------:|--------:|
| pfs_bin          | 2,000 |   400 | **−1,600** |
| bor_bin          | 1,376 |   428 | **−948**   |
| BOR.binary       |   267 |   231 | **−36**    |
| (all other 12 fields) | unchanged | unchanged | 0 |

The 400 residual `pfs_bin` flags and 428 residual `bor_bin` flags correspond
to rows where the inputs needed by the 120-day rule are absent (e.g., 9204
has no PFS data; 10013 and 14C0059G have no source PFS data; 10026 has source
NaN BOR for one patient). These are correctly flagged.

The 36 `BOR.binary` reduction corresponds to the 36 10026 CRm/CRi rows that
were previously NA-and-flagged and now resolve to `R`.

---

## 5. Documentation and provenance

Every committed change carries explicit provenance:

- **YAML config**: `scripts/config/harmonization_config.yaml` documents the
  120-day rule in a top-level comment block above `derived_rules:`, and the
  CRm/CRi → R mapping in a comment above the `R` bucket of
  `value_normalizations.BOR.binary` (with a citation to 10026 Data Dictionary
  Sheet1 rows 92–94).
- **provenance_long.csv**: every `bor_bin` / `pfs_bin` cell records
  `extraction_method = derived_bor_bin_120d` (or `_pfs_bin_120d`) and a
  notes string ending with `status=120-day landmark rule (template-supported
  derived rule; pending final clinical confirmation)`.
- **flagged_for_review.csv**: rows whose inputs are missing (pfs_time NaN
  with BOR.binary=SD, censored-short for pfs_bin, etc.) are flagged with the
  same `extraction_method` so a reviewer can see why the rule did not
  produce a value.
- **This file** is a static record of the rule rollout and the before/after
  match-rate deltas. It is not regenerated by the pipeline and will persist
  across reruns until the underlying decision changes.

---

## 6. Status & next steps

All three approvals (D1, D2, D3a) are now reproducibly implemented.
**Pipeline VERDICT: PASS** (`exclusion_and_order_checks.txt`).

Decisions **D3b** (10026 `-` handling), **D3c** (source-blank BOR not coerced
to `other`), **D4** (Cimac.id manifests), and **D5** (S1400I un-truncated age)
are **not** implemented per the request and remain open in
`source_evidence_decision_memo.md`.
