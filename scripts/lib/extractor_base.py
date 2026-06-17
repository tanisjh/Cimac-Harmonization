"""
extractor_base.py — Base class for per-trial extractors.

Each trial extractor subclasses BaseExtractor and implements `extract()`,
which yields Cell objects (one per (cimac_part_id, Cimac.id, Collection_Event, field) tuple).

The base class provides:
  - Path-resolving file accessors (with snapshot selection)
  - CIDC-aware CSV reading
  - Value normalization helpers
  - Standard yield helpers
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

import pandas as pd

from .cidc_io import read_cidc_csv
from .normalize import (
    derive_bor_binary,
    derive_bor_bin,
    derive_pfs_bin,
    normalize,
)
from .provenance import Cell

LOG = logging.getLogger("extractor")


class BaseExtractor:
    """Subclass per trial; override `extract()` to emit Cell objects."""

    trial_dir_name: str            # e.g. "EAY131-Z1D-clinical"
    template_trial_name: str       # e.g. "EAY131_Z1D"

    def __init__(self, project_root: Path, anchor_df: pd.DataFrame, trial_config: dict,
                 value_norms: dict, derived_rules: dict | None = None):
        """
        Args:
            project_root: filesystem root that contains *-clinical/ dirs
            anchor_df:    rows from the template CSV for this trial (the row anchors)
            trial_config: section of harmonization_config.yaml for this trial
            value_norms:  the global `value_normalizations` block
            derived_rules: the global `derived_rules` block (landmark parameters)
        """
        self.project_root = Path(project_root)
        self.trial_dir = self.project_root / self.trial_dir_name
        self.anchor = anchor_df.reset_index(drop=True)
        self.cfg = trial_config or {}
        self.value_norms = value_norms or {}
        self.derived_rules = derived_rules or {}
        # Cache of loaded source frames keyed by (filename or filename::sheet)
        self._cache: dict[str, pd.DataFrame] = {}

    # ── source-file access ───────────────────────────────────────────────────
    def src_path(self, key: str) -> Path:
        """Resolve a key in cfg['sources'] to a Path under the trial dir."""
        rel = (self.cfg.get("sources") or {}).get(key)
        if rel is None:
            raise KeyError(f"No source '{key}' configured for trial {self.trial_dir_name}")
        return self.trial_dir / rel

    def load_csv(self, key: str) -> pd.DataFrame:
        path = self.src_path(key)
        ck = str(path)
        if ck not in self._cache:
            r = read_cidc_csv(path)
            if r.note:
                LOG.warning("CSV read note for %s: %s", path.name, r.note)
            self._cache[ck] = r.df
        return self._cache[ck]

    def load_xlsx(self, key: str, sheet: str | int | None = None) -> pd.DataFrame:
        path = self.src_path(key)
        ck = f"{path}::{sheet}"
        if ck not in self._cache:
            self._cache[ck] = pd.read_excel(path, sheet_name=sheet) if sheet is not None else pd.read_excel(path)
        return self._cache[ck]

    # ── value-extraction helpers ────────────────────────────────────────────
    def get_norm_rules(self, harmonized_field: str) -> list | dict | None:
        return self.value_norms.get(harmonized_field)

    def normalize_value(self, harmonized_field: str, raw_value):
        rules = self.get_norm_rules(harmonized_field)
        rules_list = rules if isinstance(rules, list) else None
        return normalize(harmonized_field, raw_value, rules_list)

    # ── derived-field helpers ───────────────────────────────────────────────
    def derive_BOR_binary(self, bor_value):
        # Method name kept for internal callers; the YAML key + output column
        # were renamed BOR.binary → clinical_benefit.binary on 2026-05-20.
        rules = self.value_norms.get("clinical_benefit.binary")
        return derive_bor_binary(bor_value, rules if isinstance(rules, dict) else None)

    def derive_bor_bin(self, bor_binary, pfs_time=None):
        """120-day SD-landmark rule. Landmark pulled from derived_rules in YAML
        config (default 120). See scripts/lib/normalize.py for the rule."""
        landmark = float(self.derived_rules.get("bor_bin_landmark_days", 120))
        return derive_bor_bin(bor_binary, pfs_time, landmark_days=landmark)

    def derive_pfs_bin(self, pfs_time, pfs_stat=None):
        """120-day landmark rule. Landmark pulled from derived_rules in YAML
        config (default 120). See scripts/lib/normalize.py for the rule."""
        landmark = float(self.derived_rules.get("pfs_bin_landmark_days", 120))
        return derive_pfs_bin(pfs_time, pfs_stat, landmark_days=landmark)

    # ── Cell construction ────────────────────────────────────────────────────
    def cell(self, anchor_row, harmonized_field, value, confidence, source_file, source_column, source_row_idx, extraction_method, notes=""):
        return Cell(
            trial=self.template_trial_name,
            cimac_part_id=str(anchor_row["cimac_part_id"]),
            Cimac_id=str(anchor_row["Cimac.id"]),
            Collection_Event=str(anchor_row["Collection_Event"]),
            harmonized_field=harmonized_field,
            value=value,
            confidence=float(confidence),
            source_file=source_file,
            source_column=source_column,
            source_row_idx=source_row_idx,
            extraction_method=extraction_method,
            notes=notes,
        )

    # ── must override ────────────────────────────────────────────────────────
    def extract(self) -> Iterator[Cell]:
        raise NotImplementedError(f"{self.__class__.__name__}.extract() not implemented")
