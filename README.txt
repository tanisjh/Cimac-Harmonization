CIMAC clinical harmonization pipeline
=====================================

PROJECT PURPOSE
---------------
This repository harmonizes clinical data across 11 cancer clinical trials
using reproducible Python scripts. It reproduces the 9-trial harmonized
template (cross_trial_analysis_egk_april30_meta_9trials.csv) from source
files and extends the harmonization to 2 additional trials (10013,
14C0059G).

BACCI-clinical was previously evaluated but is NOT part of the CIMAC
trial set; the source directory has been removed and the trial is
excluded from registration in scripts/extract_harmonized_clinical.py
and scripts/config/harmonization_config.yaml. scripts/extractors/bacci.py
remains on disk for history only.


DIRECTORY ASSUMPTIONS
---------------------
- Trial source directories are in the project root and named
  "{trial_name}-clinical".
- The 9-trial template file is at the project root:
      ./cross_trial_analysis_egk_april30_meta_9trials.csv


INSTALLATION
------------
Python 3.10 is required. Set up a virtual environment and install
dependencies:

    python3.10 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt


INPUT FILES REQUIRED
--------------------
- All 11 "{trial_name}-clinical" directories at the project root:
    9204-clinical/        10013-clinical/      10021-clinical/
    10026-clinical/       10104-clinical/      14C0059G-clinical/
    ABTC1603-clinical/    E4412-clinical/      EAY131-Z1D-clinical/
    GU16-257-clinical/    S1400I-clinical/
- ./cross_trial_analysis_egk_april30_meta_9trials.csv
- scripts/ directory (all pipeline scripts and extractors)
- scripts/config/harmonization_config.yaml (single source of truth for
  per-trial mappings, value normalizations, and confidence thresholds)


COMMANDS TO RUN
---------------
After activating .venv, the full pipeline can be run two ways.

Option 1 — one-command wrapper (recommended):

    ./scripts/run_full_harmonization.sh

The wrapper uses `set -euo pipefail` and stops immediately on any failure.
It prints a labelled step header for each of the 9 stages.

Option 2 — individual commands (for debugging or partial reruns):

    # 1. Inspect source files and build a fresh inventory (optional unless
    #    source files have changed since the last run).
    python scripts/inspect_trial_files.py

    # 2. Run the harmonization pipeline. Produces the harmonized CSVs,
    #    provenance log, and flagged-for-review file.
    python scripts/extract_harmonized_clinical.py

    # 3. Validate the 9-trial reproduction against the template.
    python scripts/validate_extractions.py

    # 4. Generate the human-review summary and source-evidence report.
    python scripts/generate_review_report.py

    # 5. Generate the prioritized open-issues checklist.
    python scripts/build_review_checklist.py

    # 6. Generate the per-cell non-perfect-match review.
    python scripts/build_nonperfect_match_review.py

    # 7. Generate the GU16-257 pfs_time fallback investigation report.
    python scripts/build_gu16257_pfs_time_investigation.py

    # 8. Generate the final reviewer handoff report.
    python scripts/build_final_handoff.py

    # 9. Generate the BACCI-exclusion + 9-trial row-order check file
    #    (exclusion_and_order_checks.txt). Runs last so it can audit the
    #    freshly written handoff report. build_final_handoff.py
    #    special-cases this filename so it is not reported as "(missing)".
    python scripts/build_exclusion_and_order_checks.py

All steps after step 2 read previously generated outputs from
harmonization_outputs/ and write new files there. None of them modify
harmonized CSV values.


EXPECTED OUTPUTS IN harmonization_outputs/
------------------------------------------

Core outputs:
- harmonized_9trials_reproduced.csv
    Reproduction of the original 9-trial template (1,781 rows). Rows are
    sorted to match the row order of
    cross_trial_analysis_egk_april30_meta_9trials.csv so the file can be
    diffed against the template directly. See row_order_diagnostics.csv.
- harmonized_11trials.csv
    Final 11-trial harmonized table (9 template trials + 2 new:
    10013, 14C0059G). Replaces the previously generated
    harmonized_12trials.csv (which included BACCI and is no longer
    produced).
- row_order_diagnostics.csv
    Audit of the 9-trial alignment (issue_type ∈ {summary,
    in_template_not_in_reproduced, in_reproduced_not_in_template,
    duplicate_key_in_template, duplicate_key_in_reproduced}). For a
    healthy run only the `summary` row is present.
- provenance_long.csv
    One row per extracted cell. See "Explanation of provenance_long.csv"
    below.
- flagged_for_review.csv
    Cells that did not meet the per-field confidence threshold. See
    "Explanation of flagged_for_review.csv" below.
- validation_report.csv
    Cell-level mismatches between the reproduced 9-trial output and the
    template.
- validation_summary.csv
    Per-(trial, column) match rate against the template.
- exclusion_and_order_checks.txt
    Quick post-run checks: trial count, BACCI exclusion, 9-trial row
    count, whether 9-trial row order matches the template, key
    diagnostics.
- source_evidence_report.csv
    Per (trial, harmonized_field): which source files/columns fed the
    value, which extraction methods were used, and the confidence
    distribution.
- template_anomalies.csv
    Known data-quality anomalies in the original 9-trial template
    (sex-in-arm leak, mixed casing). Preserved verbatim in the reproduction.

Reviewer-facing outputs:
- final_handoff_report.md
    Generated by the pipeline. Narrative + per-trial breakdown with
    committed assumptions, hypotheses not committed, and recommended
    next steps. DO NOT EDIT MANUALLY.
- final_handoff_report.csv
    Flat (trial, field, status, n_rows, match_rate, action) table.
- review_priority_checklist.md
- review_priority_checklist.csv
    Prioritized P1/P2/P3 open items with proposed actions.
- nonperfect_match_review.md
    Every (trial, column) cell with match_rate < 1.0 in the 9-trial
    template (excluding policy-driven unresolved fields), classified by
    severity.
- gu16257_pfs_time_fallback_investigation.md
    Read-only investigation that motivated the current GU16-257
    pfs_time fallback rule (DFSTIM if not NaN else DRFSTIM).

Inspection outputs:
- file_inventory.csv
- duplicate_files.csv
- headers_by_file.json
- inspect_summary.txt


EXPLANATION OF provenance_long.csv
----------------------------------
Every value emitted into the harmonized output is recorded as one row in
provenance_long.csv with the following columns:

  trial               Template trial name (e.g., "CIMAC-s1400i")
  cimac_part_id       Participant anchor
  Cimac.id            Sample anchor
  Collection_Event    Timepoint anchor
  harmonized_field    Target column (e.g., "race", "os_time")
  value               Extracted value, or empty/NaN
  confidence          Float in [0, 1]. Cells with confidence below the
                      per-field threshold (in harmonization_config.yaml)
                      do NOT enter the harmonized CSV; they appear in
                      flagged_for_review.csv instead.
  source_file         File that contributed the value
  source_column       Column in that file
  source_row_idx      Row index in the source file (or -1 for derived
                      values, constants, and template-anchor lookups)
  extraction_method   One of: direct, direct_numeric, value_map_trial,
                      value_map_global, value_with_fallback,
                      derived_composite, derived_bor_binary, trial_constant,
                      template_anchor_only, lookup_miss, etc.
  notes               Free-text reason/audit note (e.g., the raw source
                      value, mapping rationale, why a value was below
                      threshold).

To trace any cell in harmonized_11trials.csv back to its source, filter
provenance_long.csv by (trial, cimac_part_id, Cimac.id, Collection_Event,
harmonized_field) and read the source_file + source_column.


EXPLANATION OF flagged_for_review.csv
-------------------------------------
Whenever an extracted cell's confidence falls below the per-field threshold
configured in harmonization_config.yaml, the cell is set to NA in the
harmonized output and a row is added to flagged_for_review.csv:

  trial, cimac_part_id, Cimac.id, Collection_Event,
  harmonized_field            Target column.
  source_files                File(s) that were consulted.
  candidate_source_variables  Column(s) examined.
  observed_source_values      Raw values seen.
  proposed_mapping            What the pipeline would have emitted, but did
                              not because confidence was too low.
  confidence_score            The score that fell below threshold.
  reason_low_confidence       Why (e.g., "confidence_below_threshold",
                              "value_NA_at_extraction").
  question_for_reviewer       Specific question for human follow-up.

flagged_for_review.csv is the primary artifact for human review of
uncertain harmonizations.


KNOWN UNRESOLVED ITEMS
----------------------
These will remain unresolved unless additional source documentation or
files are supplied. They are intentionally left as NA in the harmonized
output (not silently guessed) and flagged in flagged_for_review.csv.

1. bor_bin and pfs_bin (all 9 template trials):
   The template's derivation rule does not follow BOR.binary or pfs_stat
   alone. The most likely rule is the clinical-benefit / 6-month-PFS
   landmark convention (1 iff R OR SD-with-PFS>=6mo; 1 iff PFS>=6mo OR
   censored), which matches ~78-86% of template rows. Without explicit
   original derivation rules from the analysis SAP, these fields are
   NOT committed and remain NA. See gu16257_pfs_time_fallback_investigation.md
   for the pattern this team used to commit fallback rules with strong
   evidence.

2. S1400I age:
   The template's age values are decimals (per-sample age at collection),
   while the source file age_num is integer (age at enrollment). The
   per-sample decimal age cannot be derived from available source files
   because per-sample collection dates are not present. Supplying a
   sample-collection-date file would enable this derivation.

3. Cimac.id for 10013 and 14C0059G:
   Exhaustive scans of every cell in every file in 10013-clinical/ and
   14C0059G-clinical/ found no strings matching the sample-level Cimac.id
   pattern. These trials require external CIMAC sample manifests to
   populate sample-level identifiers.


OPERATING NOTES
---------------
- No harmonized CSV should be manually edited. All changes should be made
  through scripts/config/harmonization_config.yaml (preferred) or, when
  the change requires new logic, through the relevant extractor in
  scripts/extractors/, then the pipeline should be regenerated by running
  the commands listed above.

- final_handoff_report.md is generated by the pipeline and should not be
  edited manually. The same applies to nonperfect_match_review.md and
  gu16257_pfs_time_fallback_investigation.md (both produced by their
  respective build_* scripts).

- The single source of truth for per-trial mappings, value normalizations,
  per-field confidence thresholds, and trial-specific quirks is:
      scripts/config/harmonization_config.yaml

- Adding a new trial requires (a) adding its directory under the project
  root, (b) adding its entry to harmonization_config.yaml, and (c)
  writing an extractor under scripts/extractors/ following the pattern
  of existing modules. Register the new extractor in
  scripts/extract_harmonized_clinical.py EXTRACTORS.


DIRECTORY LAYOUT
----------------
  scripts/
    run_full_harmonization.sh           # one-command wrapper (recommended)
    inspect_trial_files.py              # input file inventory
    extract_harmonized_clinical.py      # orchestrator
    validate_extractions.py             # template-vs-reproduced comparison
    generate_review_report.py           # human-review summary
    build_review_checklist.py           # prioritized P1/P2/P3 list
    build_nonperfect_match_review.py    # per-cell <1.0 match analysis
    build_gu16257_pfs_time_investigation.py
    build_final_handoff.py              # final handoff report
    config/
      harmonization_config.yaml         # single source of truth
    lib/
      cidc_io.py                        # CIDC-aware CSV reader
      extractor_base.py                 # base class
      normalize.py                      # value-normalization rules
      provenance.py                     # Cell + FlagRow dataclasses
    extractors/
      _helpers.py                       # shared helper functions
      <trial_slug>.py                   # one module per trial
  harmonization_outputs/                # all generated artifacts
  {trial_name}-clinical/                # source data (12 dirs)
  cross_trial_analysis_egk_april30_meta_9trials.csv   # template
  requirements.txt
  README.txt
