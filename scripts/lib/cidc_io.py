"""
cidc_io.py — Shared utilities for reading the heterogeneous CIDC clinical files.

CIDC convention: most per-trial CSVs have a 1-line preamble of the form
   version,<YYYY-MM-DD>
   <free-text description>,cimac_part_id,...   <-- this is the real header
followed by data. Some files (esp. 9204) skip the preamble entirely and put the
real header on row 1. We detect this by sniffing the first two lines.

Also exposes:
  - latest_snapshot(): pick the file with the newest extracted date tag
  - read_data_dictionary(): parse a trial Appendix-A / DataDictionary XLSX
    into {field_code -> {variable, label, codes:{code:value}}}
  - load_cidc_annotation(): parse a CIDC annotation Excel (the trial's own
    harmonization spec) into a list of rule rows
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd

LOG = logging.getLogger("cidc_io")

DATE_PAT = re.compile(
    r"""(
        \d{4}[-_.]\d{2}[-_.]\d{2}     |
        \d{2}[-_.]\d{2}[-_.]\d{4}     |
        \d{8}
    )""",
    re.X,
)


# --------------------------------------------------------------------------
# CSV reader
# --------------------------------------------------------------------------


@dataclass
class ReadResult:
    """Result of read_cidc_csv()."""
    df: pd.DataFrame
    preamble_skipped: bool
    encoding: str
    note: str = ""


def _peek_first_lines(path: Path, n: int = 3, encodings: Iterable[str] = ("utf-8", "latin-1", "cp1252")) -> tuple[list[str], str]:
    """Return (lines, encoding) for the first n lines of a text file."""
    last_err: Exception | None = None
    for enc in encodings:
        try:
            with path.open("r", encoding=enc, errors="strict") as f:
                lines = []
                for _ in range(n):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.rstrip("\n"))
                return lines, enc
        except UnicodeDecodeError as e:
            last_err = e
    # Last resort: latin-1 (never fails)
    with path.open("r", encoding="latin-1", errors="replace") as f:
        lines = [f.readline().rstrip("\n") for _ in range(n)]
    return lines, "latin-1"


def has_cidc_preamble(first_line: str) -> bool:
    """Heuristic: first line of a CIDC CSV starts with 'version,'."""
    return first_line.strip().lower().startswith("version,")


def read_cidc_csv(path: str | Path, *, force_skiprows: int | None = None) -> ReadResult:
    """
    Robustly read a CIDC clinical CSV. Detects 1-line preamble.

    If `force_skiprows` is given, that exact number of rows is skipped
    regardless of preamble sniffing.
    """
    p = Path(path)
    lines, enc = _peek_first_lines(p, n=3)
    if not lines:
        return ReadResult(df=pd.DataFrame(), preamble_skipped=False, encoding=enc, note="empty_file")

    skiprows = force_skiprows
    preamble_skipped = False
    if skiprows is None:
        if has_cidc_preamble(lines[0]):
            skiprows = 1
            preamble_skipped = True
        else:
            skiprows = 0

    # Try the detected encoding first, then a fallback
    for try_enc in (enc, "latin-1"):
        try:
            df = pd.read_csv(p, skiprows=skiprows, encoding=try_enc, low_memory=False)
            return ReadResult(df=df, preamble_skipped=preamble_skipped, encoding=try_enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return ReadResult(df=pd.DataFrame(), preamble_skipped=preamble_skipped, encoding=try_enc, note=f"{type(e).__name__}: {e}")
    return ReadResult(df=pd.DataFrame(), preamble_skipped=preamble_skipped, encoding="", note="decode_failed_all_encodings")


# --------------------------------------------------------------------------
# Snapshot selection
# --------------------------------------------------------------------------


def extract_date_tag(name: str) -> str:
    m = DATE_PAT.findall(name)
    return m[-1] if m else ""


def _normalize_date_tag(tag: str) -> str:
    """Convert any of the supported date formats to YYYYMMDD for sorting."""
    if not tag:
        return ""
    digits = re.sub(r"[^0-9]", "", tag)
    if len(digits) != 8:
        return ""
    # MMDDYYYY or YYYYMMDD?
    if re.match(r"^\d{4}[-_.]\d{2}[-_.]\d{2}", tag):  # YYYY-MM-DD
        return digits
    if re.match(r"^\d{2}[-_.]\d{2}[-_.]\d{4}", tag):  # MM-DD-YYYY
        return digits[4:] + digits[:4]
    # 8-digit: assume MMDDYYYY if first two ≤ 12 and not >31, else YYYYMMDD
    a, b = int(digits[:2]), int(digits[2:4])
    if a <= 12 and b <= 31:
        # ambiguous; prefer YYYYMMDD if first 4 look like a year
        year_first = int(digits[:4])
        if 2015 <= year_first <= 2035:
            return digits
        return digits[4:] + digits[:4]
    return digits


def latest_snapshot(paths: Iterable[str | Path], on_or_before: str | None = None) -> Path | None:
    """
    Given paths, return the one with the newest date tag.
    If on_or_before is set (YYYYMMDD), restrict to files dated <= that.
    """
    best: tuple[str, Path] | None = None
    for p in paths:
        p = Path(p)
        tag = _normalize_date_tag(extract_date_tag(p.name))
        if on_or_before and tag and tag > on_or_before:
            continue
        if not tag:
            tag = "00000000"
        if best is None or tag > best[0]:
            best = (tag, p)
    return best[1] if best else None


# --------------------------------------------------------------------------
# Data dictionary parsing
# --------------------------------------------------------------------------


@dataclass
class FieldDef:
    code: str                                  # e.g. "A2"
    variable: str = ""                         # e.g. "RACE"
    label: str = ""                            # e.g. "Race"
    type: str = ""                             # Char/Num
    codes: dict[str, str] = field(default_factory=dict)  # {"W":"White", "B":"Black", ...}
    source_file: str = ""
    source_sheet: str = ""


def parse_cidc_appendix_a(xlsx_path: str | Path, sheet_hints: Iterable[str] = ("Example Data Dictionaries", "Patient Demographics Dataset Dictionary", "Detailed description")) -> dict[str, FieldDef]:
    """
    Parse a CIDC Appendix-A / DataDictionary Excel into {code: FieldDef}.

    The CIDC convention is:
      - 'Column Header' (e.g. "A1", "A2") in one cell
      - 'Variable' (e.g. "RACE")
      - 'Var. Label' (e.g. "Race")
      - 'Type' (Char/Num)
      - 'Code' + 'Code Definition' for value mappings (rolls down rows)
    The code column may live across rows where Column Header is NaN.
    """
    p = Path(xlsx_path)
    try:
        xl = pd.ExcelFile(p)
    except Exception as e:
        LOG.warning("Cannot open %s: %s", p, e)
        return {}

    defs: dict[str, FieldDef] = {}
    for sn in xl.sheet_names:
        try:
            df = xl.parse(sn, header=None, dtype=str)
        except Exception:
            continue
        if df.empty:
            continue
        # Locate header row by scanning for 'Column Header' (case-insensitive)
        header_row = None
        for i in range(min(15, len(df))):
            row = df.iloc[i].astype(str).str.lower()
            if any("column header" in v for v in row) and any("variable" in v for v in row):
                header_row = i
                break
        if header_row is None:
            continue
        cols = df.iloc[header_row].astype(str).str.strip().tolist()
        body = df.iloc[header_row + 1:].copy()
        body.columns = cols

        # Identify the relevant columns
        def _col(*candidates):
            for c in candidates:
                for actual in body.columns:
                    if actual.strip().lower() == c.lower():
                        return actual
            return None

        c_code  = _col("Column Header")
        c_var   = _col("Variable")
        c_label = _col("Var. Label", "Variable Label")
        c_type  = _col("Type")
        c_code_val = _col("Code")
        c_code_def = _col("Code Definition")
        if c_code is None or c_var is None:
            continue

        current: FieldDef | None = None
        for _, row in body.iterrows():
            code = (row.get(c_code) or "").strip() if pd.notna(row.get(c_code)) else ""
            variable = (row.get(c_var) or "").strip() if pd.notna(row.get(c_var)) else ""
            label = (row.get(c_label) or "").strip() if c_label and pd.notna(row.get(c_label)) else ""
            typ = (row.get(c_type) or "").strip() if c_type and pd.notna(row.get(c_type)) else ""
            code_val = (row.get(c_code_val) or "").strip() if c_code_val and pd.notna(row.get(c_code_val)) else ""
            code_def = (row.get(c_code_def) or "").strip() if c_code_def and pd.notna(row.get(c_code_def)) else ""

            if code and re.match(r"^[A-Z]\d+[A-Za-z_0-9]*$", code):
                fd = FieldDef(code=code, variable=variable, label=label, type=typ,
                              source_file=p.name, source_sheet=sn)
                if code_val:
                    fd.codes[code_val] = code_def
                defs[code] = fd
                current = fd
            elif current is not None and code_val:
                current.codes[code_val] = code_def
            elif current is not None and variable and not current.variable:
                current.variable = variable
                current.label = label or current.label
                current.type = typ or current.type

    return defs


# --------------------------------------------------------------------------
# Convenience: discover trial files
# --------------------------------------------------------------------------


def list_trial_files(trial_dir: str | Path) -> list[Path]:
    p = Path(trial_dir)
    return sorted([q for q in p.iterdir() if q.is_file()])


def find_by_pattern(paths: Iterable[Path], *patterns: str) -> list[Path]:
    pats = [re.compile(pat, re.I) for pat in patterns]
    return [p for p in paths if any(pat.search(p.name) for pat in pats)]
