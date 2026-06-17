"""
provenance.py — Data structures for tracking provenance of every extracted cell.

A `Cell` is one harmonized (trial, cimac_part_id, Cimac.id, Collection_Event, field) value
with full source attribution. Extractors emit a stream of Cells; the orchestrator
pivots them into the wide harmonized output and writes the long form as
provenance_long.csv.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Cell:
    trial:              str            # template `trial` value, e.g. "EAY131_Z1D"
    cimac_part_id:      str            # participant ID anchor
    Cimac_id:           str            # sample ID anchor (template's Cimac.id)
    Collection_Event:   str            # event anchor (template's Collection_Event)
    harmonized_field:   str            # one of the 20 template columns
    value:              Any            # extracted value (may be None)
    confidence:         float          # [0,1]
    source_file:        str            # path relative to trial dir
    source_column:      str            # column name in source
    source_row_idx:     int | str      # row index or row description
    extraction_method:  str            # "direct" | "value_map" | "derived" | ...
    notes:              str = ""       # free-text, optional

    def as_record(self) -> dict[str, Any]:
        d = asdict(self)
        # rename Cimac_id -> Cimac.id for output consistency with the template
        d["Cimac.id"] = d.pop("Cimac_id")
        return d


@dataclass
class FlagRow:
    """A row added to flagged_for_review.csv when confidence < threshold."""
    trial:                       str
    cimac_part_id:               str
    Cimac_id:                    str
    Collection_Event:            str
    harmonized_field:            str
    source_files:                str       # semicolon-joined
    candidate_source_variables:  str       # semicolon-joined
    observed_source_values:      str       # semicolon-joined
    proposed_mapping:            str
    confidence_score:            float
    reason_low_confidence:       str
    question_for_reviewer:       str

    def as_record(self) -> dict[str, Any]:
        d = asdict(self)
        d["Cimac.id"] = d.pop("Cimac_id")
        return d
