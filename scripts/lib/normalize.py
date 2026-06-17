"""
normalize.py — Apply value_normalizations rules from the YAML config.

Returns (normalized_value, confidence, note) for an input value.
"""
from __future__ import annotations

import re
from typing import Any


def normalize(field: str, value: Any, rules: list[dict] | None) -> tuple[Any, float, str]:
    """
    Apply normalization rules to a single value.

    Rules format (from YAML):
        - {match: "...", value: "...", kind: exact|iexact|prefix|contains|regex,
           confidence: 0.0-1.0, note: "..."}
    Returns:
        (normalized_value, confidence_applied, note). If no rule matched,
        returns (value, default_confidence_if_value_else_0, "").
    """
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return None, 0.0, "input_is_NaN"

    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "na", "n/a"):
        return None, 0.0, "input_blank_or_NA"

    if not rules:
        # Numeric passthrough gets high confidence; non-numeric mid.
        try:
            float(s)
            return value, 0.95, "no_rules_numeric_passthrough"
        except (TypeError, ValueError):
            return value, 0.85, "no_rules_string_passthrough"

    for rule in rules:
        if not isinstance(rule, dict) or "match" not in rule:
            continue
        m = rule["match"]
        kind = rule.get("kind", "exact")
        try:
            matched = (
                kind == "exact"    and s == str(m) or
                kind == "iexact"   and s.lower() == str(m).lower() or
                kind == "prefix"   and s.lower().startswith(str(m).lower()) or
                kind == "contains" and str(m).lower() in s.lower() or
                kind == "regex"    and re.search(str(m), s)
            )
        except re.error:
            matched = False
        if matched:
            return rule.get("value", value), float(rule.get("confidence", 0.7)), rule.get("note", "")
    return value, 0.5, "no_matching_rule_passthrough"


def derive_bor_binary(bor: Any, rules: dict | None) -> tuple[str | None, float, str]:
    """Apply the BOR -> BOR.binary rule from value_normalizations."""
    if bor is None or (isinstance(bor, float) and bor != bor):
        return None, 0.0, "BOR_is_NaN"
    s = str(bor).strip()
    if not rules:
        return None, 0.0, "no_BOR_binary_rules"
    for binary_value, source_values in rules.items():
        if s in source_values or s.upper() in [str(v).upper() for v in source_values]:
            return binary_value, 0.95, f"BOR={s!r} matched {binary_value}"
    return None, 0.4, f"BOR={s!r} did not match any BOR.binary bucket"


def _is_nan(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and v != v:
        return True
    if isinstance(v, str) and v.strip().lower() in ("", "nan", "na", "n/a", "none"):
        return True
    return False


def _to_float(v: Any):
    if _is_nan(v):
        return None
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def derive_bor_bin(bor_binary: Any, pfs_time: Any = None, landmark_days: float = 120.0
                  ) -> tuple[int | None, float, str]:
    """Apply the 120-day SD-landmark rule to derive bor_bin from BOR.binary.

    Rule (template-supported derived rule; pending final clinical confirmation):
        bor_bin = 1   iff BOR.binary == 'R'  OR  (BOR.binary == 'SD' AND pfs_time ≥ landmark_days)
        bor_bin = 0   iff BOR.binary == 'NR' OR  (BOR.binary == 'SD' AND pfs_time <  landmark_days)
        bor_bin = NaN otherwise (BOR.binary ∈ {other, NaN, unrecognized})

    Empirical fit against the 9-trial template: 100% match on all 9 trials
    at landmark_days=120 (see harmonization_outputs/source_evidence_discrepancy_report.md §1).
    """
    if _is_nan(bor_binary):
        return None, 0.0, "BOR.binary_is_NaN"
    s = str(bor_binary).strip()
    if s == "R":
        return 1, 0.95, f"BOR.binary='R' -> bor_bin=1 (120-day rule)"
    if s == "NR":
        return 0, 0.95, f"BOR.binary='NR' -> bor_bin=0 (120-day rule)"
    if s == "SD":
        t = _to_float(pfs_time)
        if t is None:
            return None, 0.30, (
                f"BOR.binary='SD' but pfs_time={pfs_time!r} is not numeric; "
                f"cannot apply 120-day landmark"
            )
        if t >= landmark_days:
            return 1, 0.95, (
                f"BOR.binary='SD' AND pfs_time={t}>={landmark_days} -> bor_bin=1 "
                f"(120-day SD landmark; template-supported, pending clinical confirmation)"
            )
        return 0, 0.95, (
            f"BOR.binary='SD' AND pfs_time={t}<{landmark_days} -> bor_bin=0 "
            f"(120-day SD landmark; template-supported, pending clinical confirmation)"
        )
    # other / CRm / CRi (legacy) / unrecognized → NaN by design
    return None, 0.95, (
        f"BOR.binary={s!r} -> bor_bin=NaN by rule "
        f"(non-{'R'!r}/{'NR'!r}/{'SD'!r} BOR.binary values are intentionally NaN)"
    )


def derive_pfs_bin(pfs_time: Any, pfs_stat: Any = None, landmark_days: float = 120.0
                  ) -> tuple[int | None, float, str]:
    """Apply the 120-day landmark rule to derive pfs_bin.

    Rule (template-supported derived rule; pending final clinical confirmation):
        pfs_bin = 1   iff pfs_time ≥ landmark_days
        pfs_bin = 0   iff pfs_time < landmark_days AND pfs_stat == 1
        pfs_bin = NaN iff pfs_time < landmark_days AND pfs_stat == 0
                  (censored before the landmark cannot be classified)

    Empirical fit against the 9-trial template: 100% match on all 8 trials
    with non-trivial pfs_bin at landmark_days=120 (see source_evidence_discrepancy_report.md §2).
    """
    t = _to_float(pfs_time)
    if t is None:
        return None, 0.30, f"pfs_time={pfs_time!r} not numeric — cannot apply 120-day landmark"
    if t >= landmark_days:
        return 1, 0.95, (
            f"pfs_time={t}>={landmark_days} -> pfs_bin=1 "
            f"(120-day landmark; template-supported, pending clinical confirmation)"
        )
    # pfs_time < landmark_days: need pfs_stat to disambiguate event vs censored
    ps = _to_float(pfs_stat)
    if ps is None:
        return None, 0.30, (
            f"pfs_time={t}<{landmark_days} but pfs_stat={pfs_stat!r} not 0/1 — "
            f"cannot disambiguate event vs censored"
        )
    if int(ps) == 1:
        return 0, 0.95, (
            f"pfs_time={t}<{landmark_days} AND pfs_stat=1 -> pfs_bin=0 "
            f"(event before landmark; template-supported, pending clinical confirmation)"
        )
    if int(ps) == 0:
        # Template intentionally leaves these as NaN (censored before landmark)
        return None, 0.95, (
            f"pfs_time={t}<{landmark_days} AND pfs_stat=0 -> pfs_bin=NaN "
            f"(censored before landmark; matches template; pending clinical confirmation)"
        )
    return None, 0.30, f"pfs_stat={pfs_stat!r} not 0/1"
