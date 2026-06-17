# Human-review checklist — CIMAC harmonization

Generated from current `harmonization_outputs/` state. **Do not** modify harmonized CSVs while addressing these items; instead edit `scripts/config/harmonization_config.yaml` and re-run the pipeline.

## P1 — 5 items

### 10104 · `os_time / pfs_time`

- **Issue type:** source_column_choice
- **Rows affected:** 213
- **Current behavior:** Currently picking the 'from PT_REG_DT_INT' columns; matches 10% of template rows. Most values differ substantially.
- **Candidate source files:** 10104_armaandb_response_pfsos_treatment_update.2023-04-04.csv, 10104_armc_response_pfsos_treatment_update16mar2023.2023-04-04.csv
- **Candidate source columns:** Per file there are TWO sets of survival columns: (a) from PT_REG_DT_INT (registration date) and (b) from first_cycle_first_day. Template values likely use the first_cycle_first_day variant.
- **Evidence:** Match rate 0.099 (os_time) / 0.113 (pfs_time). Same patient rows show source PT_REG_DT_INT values diverging from template by ~5-30 days.
- **Question for reviewer:** Confirm template's 10104 os_time/pfs_time are anchored to first_cycle_first_day (not PT_REG_DT_INT). If yes, we just swap the column choice.
- **Recommended next action:** Update response_columns_aandb / response_columns_armc in YAML to use the 'first_cycle_first_day' columns; re-run pipeline.

### CIMAC-e4412 · `os_time / pfs_time`

- **Issue type:** unit_conversion_or_anchor
- **Rows affected:** 167
- **Current behavior:** Multiplying weeks × 7 (os_wk → os_time days); 0% match.
- **Candidate source files:** baseline_outcomes.xlsx (Sheet1)
- **Candidate source columns:** os_wk, pfs_wk (weeks since enrollment), BRENTUXIMAB_STRT_fr_enrol / NIVOLUMAB_STRT_fr_enrol / LAST_PROT_TX_fr_enrol (week offsets to other events).
- **Evidence:** Source os_wk first row = 1.56879 (weeks); × 7 = ~11 days. Template os_time for E4412 has ranges in hundreds of days. Suggests either (a) different anchor (e.g., from diagnosis rather than enrollment) or (b) a different column.
- **Question for reviewer:** Is template E4412 os_time defined as weeks×7 from enrollment, or from a different anchor (e.g., diagnosis, treatment start)? Same for pfs_time.
- **Recommended next action:** Compare per-patient os_time template values to (os_wk × 7) + (LAST_PROT_TX_fr_enrol × 7) to identify the anchor. Adjust YAML.

### CIMAC-e4412 · `treatment`

- **Issue type:** value_map_incomplete
- **Rows affected:** 167
- **Current behavior:** Mapping PROT_TX_ARM_ASS_TXT one-letter codes (E→BV+ipi, G→BV+nivo+ipi, Other→BV+nivo). Match 0.293.
- **Candidate source files:** baseline_outcomes.xlsx (PROT_TX_ARM_ASS_TXT), CIDC_Annotations_E4412_20230327.xlsx (arm codebook?)
- **Candidate source columns:** PROT_TX_ARM_ASS_TXT — values seen: E, G, plus possibly C/D/F. Codebook tab in adverse_events.xlsx / treatment.xlsx may list mapping.
- **Evidence:** Template treatment values for E4412: BV+ipi (67), BV+nivo+ipi (52), BV+nivo (48) = 167. Our E→BV+ipi covers part of these but the other letters are not yet decoded.
- **Question for reviewer:** Provide (or confirm in the codebook) the mapping for every PROT_TX_ARM_ASS_TXT letter code → treatment label.
- **Recommended next action:** Open the Codebook sheet of treatment.xlsx (12 rows) — the arm decoding is almost certainly there. Update YAML treatment_per_arm with the full mapping.

### CIMAC-gu16257 · `clinical_benefit`

- **Issue type:** value_map_incomplete
- **Rows affected:** 196
- **Current behavior:** Currently mapping source RESPTYPE R→Y, N→N, NE→NE; match 0.571.
- **Candidate source files:** response.2023-01-04.csv (RESPTYPE, CLCRFL, CYSTSTAT, RECCUR)
- **Candidate source columns:** Combinations of multiple response flags — RESPTYPE alone seems insufficient. CLCRFL (clinical complete response flag) may be the stronger predictor.
- **Evidence:** Template GU16-257 clinical_benefit: Y=112, N=78, NE=6 (total 196). Source RESPTYPE alone gives ~57% match. Other response flags exist and may combine.
- **Question for reviewer:** How is GU16-257 clinical_benefit Y/N/NE derived from response.csv? Single column? Composite of CLCRFL + RECCUR?
- **Recommended next action:** Compute combinations of (RESPTYPE, CLCRFL, RECCUR) per row and find the rule that reproduces template clinical_benefit. Likely a 2-line Python check on the response file.

### CIMAC-gu16257 · `phase`

- **Issue type:** source_field_unknown
- **Rows affected:** 196
- **Current behavior:** Emitted with confidence 0.30 → NA + flagged. Match 0.015.
- **Candidate source files:** data_dictionary.2023-01-19.xlsx, response.2023-01-04.csv (RESPTYPE), disease.2023-01-04.csv, treatment.2023-01-04.csv
- **Candidate source columns:** Unknown. Template phase Y=24 / N=169 / NaN=3 — a binary indicator (NOT phase I/II). Possibly tied to a treatment-completion flag or a sub-cohort.
- **Evidence:** Template's 'phase' column for GU16-257 holds Y/N (not phase I/II). Source has 'CLCRFL' (clinical complete response flag) Y/N which has the right cardinality. Worth testing.
- **Question for reviewer:** What does the GU16-257 template 'phase' Y/N actually encode? Is it CLCRFL or another response.csv flag?
- **Recommended next action:** Cross-tab template phase against response.csv columns (CLCRFL, CYSTSTAT, RESPTYPE) per cimac_part_id to identify the source. Then add a phase column in YAML.

## P2 — 12 items

### 10013 · `Cimac.id`

- **Issue type:** cimac_id_absent_in_source
- **Rows affected:** 196
- **Current behavior:** All 196 anchor rows emit Cimac.id=NA + flagged. P2 pass performed an exhaustive scan of every cell of every file in 10013-clinical/ for strings starting with any known cimac_part_id (7-char prefix) followed by a sample-suffix: zero hits.
- **Candidate source files:** specimen_collection_2023-09-13.csv (cimac_part_id + M-codes only)
- **Candidate source columns:** M6 (sample type), M7 (visit), M2 (days), M4 (anatomic site) — no sample identifier
- **Evidence:** Confirmed: no column in any 10013 file holds sample-level Cimac.id. External CIMAC manifest is the only way to populate this column.
- **Question for reviewer:** Is there a CIMAC sample manifest for 10013 we can be pointed to? (Path / Google Drive / ShipRamp export.)
- **Recommended next action:** Place the manifest file under 10013-clinical/ and update YAML source mapping. Without it, harmonized rows ship with NA Cimac.id.

### 10013 · `arm`

- **Issue type:** high_flag_volume
- **Rows affected:** 196
- **Current behavior:** 196 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 196 cells in 10013 have confidence below threshold for arm.
- **Question for reviewer:** Is there a known authoritative source for 10013 arm that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10013' & harmonized_field=='arm', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10013 · `clinical_benefit.binary`

- **Issue type:** high_flag_volume
- **Rows affected:** 196
- **Current behavior:** 196 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 196 cells in 10013 have confidence below threshold for clinical_benefit.binary.
- **Question for reviewer:** Is there a known authoritative source for 10013 clinical_benefit.binary that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10013' & harmonized_field=='clinical_benefit.binary', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10013 · `os_stat`

- **Issue type:** high_flag_volume
- **Rows affected:** 196
- **Current behavior:** 196 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 196 cells in 10013 have confidence below threshold for os_stat.
- **Question for reviewer:** Is there a known authoritative source for 10013 os_stat that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10013' & harmonized_field=='os_stat', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10013 · `os_time`

- **Issue type:** high_flag_volume
- **Rows affected:** 196
- **Current behavior:** 196 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 196 cells in 10013 have confidence below threshold for os_time.
- **Question for reviewer:** Is there a known authoritative source for 10013 os_time that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10013' & harmonized_field=='os_time', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10013 · `pfs_stat`

- **Issue type:** high_flag_volume
- **Rows affected:** 196
- **Current behavior:** 196 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 196 cells in 10013 have confidence below threshold for pfs_stat.
- **Question for reviewer:** Is there a known authoritative source for 10013 pfs_stat that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10013' & harmonized_field=='pfs_stat', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10013 · `pfs_time`

- **Issue type:** high_flag_volume
- **Rows affected:** 196
- **Current behavior:** 196 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 196 cells in 10013 have confidence below threshold for pfs_time.
- **Question for reviewer:** Is there a known authoritative source for 10013 pfs_time that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10013' & harmonized_field=='pfs_time', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10026 · `clinical_benefit.binary`

- **Issue type:** template_match_low
- **Rows affected:** 207
- **Current behavior:** Match rate 0.748 across 214 rows (160 match / 54 mismatch).
- **Candidate source files:** (see provenance_long.csv for this (trial, field))
- **Candidate source columns:** (see provenance_long.csv)
- **Evidence:** Validation: template_match_rate=0.748. Investigate specific rows via validation_report.csv filter trial=='10026' & column=='clinical_benefit.binary'.
- **Question for reviewer:** What source column or transformation should be used for 10026 clinical_benefit.binary to better match the template?
- **Recommended next action:** Inspect validation_report.csv for 10026/clinical_benefit.binary; identify the divergence pattern; refine value_map or column choice in harmonization_config.yaml; re-run pipeline.

### 10026 · `phase`

- **Issue type:** high_flag_volume
- **Rows affected:** 207
- **Current behavior:** 207 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 207 cells in 10026 have confidence below threshold for phase.
- **Question for reviewer:** Is there a known authoritative source for 10026 phase that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10026' & harmonized_field=='phase', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 10104 · `phase`

- **Issue type:** high_flag_volume
- **Rows affected:** 213
- **Current behavior:** 213 rows flagged for review (NA in harmonized output).
- **Candidate source files:** (see flagged_for_review.csv source_files col)
- **Candidate source columns:** (see flagged_for_review.csv candidate_source_variables col)
- **Evidence:** 213 cells in 10104 have confidence below threshold for phase.
- **Question for reviewer:** Is there a known authoritative source for 10104 phase that the pipeline missed?
- **Recommended next action:** Filter flagged_for_review.csv to trial=='10104' & harmonized_field=='phase', inspect notes / proposed_mapping; decide whether the field is genuinely unrecoverable from source (then accept NA) or the YAML config needs a new column / value_map.

### 14C0059G · `Cimac.id`

- **Issue type:** cimac_id_absent_in_source
- **Rows affected:** 22
- **Current behavior:** All 23 anchor rows emit Cimac.id=NA + flagged. P2 pass scanned all 26 files for any string starting with a known cimac_part_id (e.g., CA44FBW) followed by a sample suffix: zero hits.
- **Candidate source files:** research_sample_collection_apheresis.csv (cimac_part_id + Visit + Days only)
- **Candidate source columns:** (no sample-level id column)
- **Evidence:** Confirmed: 14C0059G has no CIDC annotation file and no specimen-linkage table with Cimac.id. External manifest required.
- **Question for reviewer:** Is there a CIMAC manifest or assay-shipping log for 14C0059G that maps (Patient, Visit) → Cimac.id?
- **Recommended next action:** Add the manifest to 14C0059G-clinical/ and configure as the source for Cimac.id in the YAML.

### 14C0059G · `age`

- **Issue type:** source_field_missing
- **Rows affected:** 22
- **Current behavior:** Emitted with confidence 0.30 → NA + flagged for all rows.
- **Candidate source files:** patient_demographics_all.csv (8 cols, no Age column)
- **Candidate source columns:** (none)
- **Evidence:** Source demographics file has Race, Gender, Ethnicity, ECOG cols but no Age column. enrollment.csv lacks age too.
- **Question for reviewer:** Is there a separate age-at-enrollment file for 14C0059G? Or is age intentionally omitted (e.g., PHI redaction)?
- **Recommended next action:** If age intentionally redacted, document in the trial-level notes and lower the age threshold for this trial only. Otherwise obtain age data.

## P3 — 6 items

### 10104 · `clinical_benefit.binary`

- **Issue type:** template_match_low
- **Rows affected:** 213
- **Current behavior:** Match rate 0.920 across 213 rows (196 match / 17 mismatch).
- **Candidate source files:** (see provenance_long.csv for this (trial, field))
- **Candidate source columns:** (see provenance_long.csv)
- **Evidence:** Validation: template_match_rate=0.920. Investigate specific rows via validation_report.csv filter trial=='10104' & column=='clinical_benefit.binary'.
- **Question for reviewer:** What source column or transformation should be used for 10104 clinical_benefit.binary to better match the template?
- **Recommended next action:** Inspect validation_report.csv for 10104/clinical_benefit.binary; identify the divergence pattern; refine value_map or column choice in harmonization_config.yaml; re-run pipeline.

### 10104 · `os_stat`

- **Issue type:** template_match_low
- **Rows affected:** 213
- **Current behavior:** Match rate 0.920 across 213 rows (196 match / 17 mismatch).
- **Candidate source files:** (see provenance_long.csv for this (trial, field))
- **Candidate source columns:** (see provenance_long.csv)
- **Evidence:** Validation: template_match_rate=0.920. Investigate specific rows via validation_report.csv filter trial=='10104' & column=='os_stat'.
- **Question for reviewer:** What source column or transformation should be used for 10104 os_stat to better match the template?
- **Recommended next action:** Inspect validation_report.csv for 10104/os_stat; identify the divergence pattern; refine value_map or column choice in harmonization_config.yaml; re-run pipeline.

### ABTC1603 · `pfs_stat`

- **Issue type:** template_match_low
- **Rows affected:** 145
- **Current behavior:** Match rate 0.899 across 148 rows (133 match / 15 mismatch).
- **Candidate source files:** (see provenance_long.csv for this (trial, field))
- **Candidate source columns:** (see provenance_long.csv)
- **Evidence:** Validation: template_match_rate=0.899. Investigate specific rows via validation_report.csv filter trial=='ABTC1603' & column=='pfs_stat'.
- **Question for reviewer:** What source column or transformation should be used for ABTC1603 pfs_stat to better match the template?
- **Recommended next action:** Inspect validation_report.csv for ABTC1603/pfs_stat; identify the divergence pattern; refine value_map or column choice in harmonization_config.yaml; re-run pipeline.

### ALL (9 template trials) · `bor_bin`

- **Issue type:** unresolved_derivation
- **Rows affected:** 1771
- **Current behavior:** NA in harmonized output; row added to flagged_for_review.csv per policy. NOT derived because rule isn't pinned down.
- **Candidate source files:** DERIVED from clinical_benefit.binary + pfs_time
- **Candidate source columns:** clinical_benefit.binary, pfs_time
- **Evidence:** Across 9 template trials, clinical_benefit.binary=SD splits 99/178 between bor_bin=0/1 (clearly not a function of clinical_benefit.binary alone). Mean pfs_time differs: 83d for bor_bin=0, 266d for bor_bin=1. Hypothesis `1 iff R OR (SD AND pfs_time>=183)` matches 86% of CIMAC-s1400i rows and 78% of EAY131_Z1D — close to the standard 'clinical benefit rate' definition but not perfect.
- **Question for reviewer:** Is bor_bin the standard clinical-benefit indicator (CR/PR plus SD lasting >=6 months), and what is the exact PFS threshold (days) for each trial?
- **Recommended next action:** Provide the operational definition from the original analysis plan (or pointer to the statistician). Once confirmed, add a single derivation block in harmonization_config.yaml (bor_bin_rule: {threshold_days: N, criteria: ...}) and the extractor helper will emit it with high confidence.

### ALL (9 template trials) · `pfs_bin`

- **Issue type:** unresolved_derivation
- **Rows affected:** 1771
- **Current behavior:** NA in harmonized output; flagged for every row.
- **Candidate source files:** DERIVED from pfs_stat + pfs_time
- **Candidate source columns:** pfs_stat, pfs_time
- **Evidence:** Template pfs_bin does NOT mirror pfs_stat (counter-examples in every trial). Hypothesis `1 iff pfs_time>=183 OR pfs_stat=0` matches 81% on CIMAC-s1400i and 81% on EAY131_Z1D — suggestive of a 6-month PFS landmark indicator but not exact.
- **Question for reviewer:** What is the canonical pfs_bin rule? Standard candidates: (a) 6-month PFS landmark, (b) 4-month PFS, (c) trial-specific.
- **Recommended next action:** Confirm rule + threshold; commit to harmonization_config.yaml.

### CIMAC-s1400i · `age`

- **Issue type:** source_data_not_derivable
- **Rows affected:** 561
- **Current behavior:** Emitted with confidence 0.55 (below 0.80 threshold) → NA in harmonized output; row flagged.
- **Candidate source files:** Clinical Dataset 2023_03_14.csv (age_num)
- **Candidate source columns:** age_num (integer, age at enrollment)
- **Evidence:** Template age values are decimals (e.g., 50.5, 47.9, 79.3); source `age_num` is integer (enrollment age). Difference is sample-time offset, which requires per-sample collection date — NOT present in any S1400I source file.
- **Question for reviewer:** Where is the per-sample collection date for S1400I stored? (External CIMAC sample manifest? Another file we missed?)
- **Recommended next action:** If sample collection dates can be supplied (CSV with cimac_part_id, Cimac.id, collection_date), the extractor will compute decimal age. Otherwise accept enrollment-age proxy with documented caveat.
