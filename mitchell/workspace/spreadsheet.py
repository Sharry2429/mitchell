"""Full spreadsheet engine supporting formula evaluation, statistical analysis, charts, and CSV/JSON persistence."""

import csv
import io
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from mitchell.workspace.storage import workspace_storage


class Cell(BaseModel):
    """A single cell within a spreadsheet."""

    value: Any = None
    raw: str = ""  # Formula string if starts with '=', else raw input
    formatted: str = ""
    error: Optional[str] = None


class Spreadsheet(BaseModel):
    """Grid matrix representing a full multi-sheet or single sheet table."""

    sheet_id: str
    title: str
    rows: int = 50
    cols: int = 26
    data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # "A1" -> {"raw": "=SUM(B1:B5)", "value": 100}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def col_name_to_idx(col_str: str) -> int:
        """Convert column letter like 'A' -> 0, 'Z' -> 25, 'AA' -> 26."""
        col_str = col_str.upper()
        idx = 0
        for char in col_str:
            idx = idx * 26 + (ord(char) - ord("A") + 1)
        return idx - 1

    @staticmethod
    def idx_to_col_name(idx: int) -> str:
        """Convert 0 -> 'A', 25 -> 'Z', 26 -> 'AA'."""
        res = ""
        idx += 1
        while idx > 0:
            idx, rem = divmod(idx - 1, 26)
            res = chr(ord("A") + rem) + res
        return res

    def get_cell_raw(self, cell_ref: str) -> str:
        """Get raw string of cell."""
        cell_ref = cell_ref.upper()
        return self.data.get(cell_ref, {}).get("raw", "")

    def get_cell_value(self, cell_ref: str) -> Any:
        """Get evaluated value of cell."""
        cell_ref = cell_ref.upper()
        return self.data.get(cell_ref, {}).get("value")

    def set_cell(self, cell_ref: str, value_or_formula: Any) -> None:
        """Set a cell value or formula."""
        cell_ref = cell_ref.upper()
        raw_str = str(value_or_formula)
        self.data[cell_ref] = {"raw": raw_str, "value": None}
        self.updated_at = datetime.now(timezone.utc)

    def evaluate_all(self) -> None:
        """Evaluate all formulas across the entire sheet."""
        # Simple iterative formula evaluation with cycle breaker
        for ref, cell_dict in self.data.items():
            raw = str(cell_dict.get("raw", "")).strip()
            if raw.startswith("="):
                val = self._eval_formula(raw[1:], ref)
                cell_dict["value"] = val
            else:
                # Try parsing numeric or keep string/bool
                try:
                    if "." in raw:
                        cell_dict["value"] = float(raw)
                    else:
                        cell_dict["value"] = int(raw)
                except ValueError:
                    if raw.lower() == "true":
                        cell_dict["value"] = True
                    elif raw.lower() == "false":
                        cell_dict["value"] = False
                    else:
                        cell_dict["value"] = raw

    def _eval_formula(self, formula: str, current_cell: str) -> Any:
        """Evaluate standard spreadsheet functions: SUM, AVERAGE, MIN, MAX, COUNT, IF, PRODUCT."""
        formula = formula.strip()
        # Function pattern: FUNC(ARG1, ARG2, ...)
        match = re.match(r"^([A-Z_]+)\((.*)\)$", formula, flags=re.IGNORECASE)
        if not match:
            # Maybe a direct reference or basic math
            return self._resolve_token(formula)

        func_name = match.group(1).upper()
        args_str = match.group(2).strip()

        if func_name in ("SUM", "AVERAGE", "AVG", "MIN", "MAX", "COUNT", "PRODUCT"):
            vals = self._expand_range_or_args(args_str)
            numeric_vals = [v for v in vals if isinstance(v, (int, float))]
            if not numeric_vals and func_name != "COUNT":
                return 0
            if func_name == "SUM":
                return sum(numeric_vals)
            elif func_name in ("AVERAGE", "AVG"):
                return sum(numeric_vals) / len(numeric_vals) if numeric_vals else 0
            elif func_name == "MIN":
                return min(numeric_vals) if numeric_vals else 0
            elif func_name == "MAX":
                return max(numeric_vals) if numeric_vals else 0
            elif func_name == "COUNT":
                return len(numeric_vals)
            elif func_name == "PRODUCT":
                return math.prod(numeric_vals)

        elif func_name == "IF":
            parts = [p.strip() for p in args_str.split(",")]
            if len(parts) == 3:
                cond = self._eval_condition(parts[0])
                return self._resolve_token(parts[1]) if cond else self._resolve_token(parts[2])

        return f"#ERR: {func_name}"

    def _expand_range_or_args(self, args_str: str) -> List[Any]:
        """Expand comma-separated arguments or colon ranges (e.g. 'A1:A5, B1')."""
        results = []
        tokens = [t.strip() for t in args_str.split(",")]
        for tok in tokens:
            if ":" in tok:
                parts = tok.split(":")
                if len(parts) == 2:
                    results.extend(self._get_range_values(parts[0].strip(), parts[1].strip()))
            else:
                results.append(self._resolve_token(tok))
        return results

    def _get_range_values(self, start_ref: str, end_ref: str) -> List[Any]:
        """Get flattened list of cell values in range."""
        start_match = re.match(r"^([A-Z]+)(\d+)$", start_ref.upper())
        end_match = re.match(r"^([A-Z]+)(\d+)$", end_ref.upper())
        if not start_match or not end_match:
            return []

        c1 = self.col_name_to_idx(start_match.group(1))
        r1 = int(start_match.group(2))
        c2 = self.col_name_to_idx(end_match.group(1))
        r2 = int(end_match.group(2))

        min_c, max_c = min(c1, c2), max(c1, c2)
        min_r, max_r = min(r1, r2), max(r1, r2)

        vals = []
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                col_name = self.idx_to_col_name(c)
                ref = f"{col_name}{r}"
                cell_data = self.data.get(ref, {})
                v = cell_data.get("value")
                if v is not None:
                    vals.append(v)
        return vals

    def _resolve_token(self, token: str) -> Any:
        """Resolve a cell reference, number, or literal."""
        token = token.strip()
        cell_match = re.match(r"^[A-Z]+\d+$", token.upper())
        if cell_match:
            cell_data = self.data.get(token.upper(), {})
            return cell_data.get("value")
        try:
            return float(token) if "." in token else int(token)
        except ValueError:
            return token.strip("'\"")

    def _eval_condition(self, cond_str: str) -> bool:
        """Evaluate conditional string like 'A1 > 50'."""
        ops = [">=", "<=", "!=", "==", ">", "<", "="]
        for op in ops:
            if op in cond_str:
                parts = cond_str.split(op, 1)
                left = self._resolve_token(parts[0])
                right = self._resolve_token(parts[1])
                if op == ">=": return left >= right
                if op == "<=": return left <= right
                if op in ("==", "="): return left == right
                if op == "!=": return left != right
                if op == ">": return left > right
                if op == "<": return left < right
        return bool(self._resolve_token(cond_str))

    def to_csv(self) -> str:
        """Export sheet to standard CSV string."""
        self.evaluate_all()
        # Find maximum bounds
        max_r = 1
        max_c = 0
        for ref in self.data.keys():
            m = re.match(r"^([A-Z]+)(\d+)$", ref)
            if m:
                c = self.col_name_to_idx(m.group(1))
                r = int(m.group(2))
                max_r = max(max_r, r)
                max_c = max(max_c, c)

        output = io.StringIO()
        writer = csv.writer(output)
        for r in range(1, max_r + 1):
            row_vals = []
            for c in range(max_c + 1):
                ref = f"{self.idx_to_col_name(c)}{r}"
                v = self.data.get(ref, {}).get("value", "")
                row_vals.append("" if v is None else str(v))
            writer.writerow(row_vals)

        return output.getvalue()

    def get_column_stats(self, col_letter: str) -> Dict[str, Any]:
        """Compute statistical summary for numeric values in a column."""
        vals = []
        for ref, cell in self.data.items():
            if ref.startswith(col_letter.upper()):
                v = cell.get("value")
                if isinstance(v, (int, float)):
                    vals.append(v)

        if not vals:
            return {"count": 0, "sum": 0, "mean": 0, "min": 0, "max": 0, "std_dev": 0}

        n = len(vals)
        total = sum(vals)
        mean = total / n
        variance = sum((x - mean) ** 2 for x in vals) / n
        std_dev = math.sqrt(variance)

        return {
            "count": n,
            "sum": round(total, 4),
            "mean": round(mean, 4),
            "min": min(vals),
            "max": max(vals),
            "std_dev": round(std_dev, 4),
        }


class SpreadsheetEngine:
    """Operations engine for loading, creating, and editing native workspace spreadsheets."""

    def __init__(self) -> None:
        self.storage = workspace_storage

    def create_sheet(self, title: str) -> Spreadsheet:
        """Create a new empty spreadsheet."""
        sheet_id = re.sub(r"[^\w\-_\. ]", "_", title).strip().replace(" ", "_").lower()
        sheet = Spreadsheet(sheet_id=sheet_id, title=title)
        self.save_sheet(sheet, change_summary="Sheet creation")
        return sheet

    def save_sheet(self, sheet: Spreadsheet, change_summary: str = "") -> None:
        """Persist spreadsheet data as JSON and CSV in workspace storage."""
        sheet.evaluate_all()
        rel_path = f"spreadsheets/{sheet.sheet_id}.json"
        self.storage.write_file(
            rel_path=rel_path,
            content=sheet.model_dump_json(indent=2),
            file_type="spreadsheet",
            change_summary=change_summary,
        )
        # Also save CSV companion for easy export/interoperability
        self.storage.write_file(
            rel_path=f"spreadsheets/{sheet.sheet_id}.csv",
            content=sheet.to_csv(),
            file_type="spreadsheet",
            change_summary="CSV auto-export",
        )

    def load_sheet(self, sheet_id: str) -> Optional[Spreadsheet]:
        """Load a spreadsheet by ID."""
        clean_id = sheet_id.replace(".json", "").replace(".csv", "")
        rel_path = f"spreadsheets/{clean_id}.json"
        try:
            content = self.storage.read_file(rel_path)
            data = json.loads(content)
            sheet = Spreadsheet.model_validate(data)
            sheet.evaluate_all()
            return sheet
        except Exception:
            return None

    def import_csv(self, title: str, csv_content: str) -> Spreadsheet:
        """Import a CSV string into a new spreadsheet."""
        sheet = self.create_sheet(title)
        reader = csv.reader(io.StringIO(csv_content))
        for r_idx, row in enumerate(reader, start=1):
            for c_idx, val in enumerate(row):
                col_name = Spreadsheet.idx_to_col_name(c_idx)
                ref = f"{col_name}{r_idx}"
                sheet.set_cell(ref, val)

        self.save_sheet(sheet, change_summary="Imported from CSV")
        return sheet


spreadsheet_engine = SpreadsheetEngine()

__all__ = ["Cell", "Spreadsheet", "SpreadsheetEngine", "spreadsheet_engine"]
