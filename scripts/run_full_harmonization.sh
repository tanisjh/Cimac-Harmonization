#!/bin/bash
# run_full_harmonization.sh — Run the full CIMAC harmonization pipeline.
#
# Executes the 8 pipeline scripts in the documented order. Stops immediately
# if any command fails.
#
# Assumes the Python virtual environment (.venv) has already been activated,
# or that `python` resolves to a Python 3.10 interpreter with the
# requirements.txt packages installed.
#
# Usage:
#     ./scripts/run_full_harmonization.sh

set -euo pipefail

# Resolve project root (parent of this script's directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "================================================================"
echo "CIMAC clinical harmonization — full pipeline"
echo "Project root: $PROJECT_ROOT"
echo "Python:       $(command -v python)"
echo "Started:      $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"

step() {
    echo
    echo "---- Step $1/9: $2 ----"
}

step 1 "Inspect trial files (file inventory + headers)"
python scripts/inspect_trial_files.py

step 2 "Extract harmonized clinical data (orchestrator)"
python scripts/extract_harmonized_clinical.py

step 3 "Validate extractions against the 9-trial template"
python scripts/validate_extractions.py

step 4 "Generate human-review summary + source evidence + template anomalies"
python scripts/generate_review_report.py

step 5 "Build prioritized review checklist (P1/P2/P3)"
python scripts/build_review_checklist.py

step 6 "Build non-perfect match review"
python scripts/build_nonperfect_match_review.py

step 7 "Build GU16-257 pfs_time fallback investigation"
python scripts/build_gu16257_pfs_time_investigation.py

step 8 "Build final handoff report"
python scripts/build_final_handoff.py

# Runs last so it can audit the freshly written handoff report for any
# unintended BACCI mentions. build_final_handoff.py special-cases this
# file (and itself) so it does not falsely report either as missing.
step 9 "Build exclusion + row-order checks"
python scripts/build_exclusion_and_order_checks.py

echo
echo "================================================================"
echo "Pipeline complete."
echo "Outputs are in: $PROJECT_ROOT/harmonization_outputs/"
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
