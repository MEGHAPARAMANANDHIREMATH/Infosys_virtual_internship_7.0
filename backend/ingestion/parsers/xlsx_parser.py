from pathlib import Path

import pandas as pd

from ingestion.exceptions import ParsingError
from ingestion.parsers.base import ParsedSegment


class XlsxParser:
    def parse(self, file_path: Path) -> list[ParsedSegment]:
        try:
            sheets = pd.read_excel(file_path, sheet_name=None, dtype=str)
            segments: list[ParsedSegment] = []
            for sheet_name, frame in (sheets or {}).items():
                columns = [str(col) for col in frame.columns]
                if columns:
                    table_text = _frame_to_pipe_table(frame, columns)
                    segments.append(
                        ParsedSegment(
                            text=(
                                f"Sheet: {sheet_name}\n"
                                f"Columns: {' | '.join(columns)}\n"
                                f"{table_text}"
                            ),
                            section=str(sheet_name),
                            extra={"source_type": "xlsx_sheet", "sheet": str(sheet_name)},
                        )
                    )
                for row_number, row in frame.iterrows():
                    parts = []
                    for column in columns:
                        value = row[column]
                        if pd.isna(value):
                            continue
                        text_value = str(value).strip()
                        if text_value and text_value.lower() != "nan":
                            parts.append(f"{column}: {text_value}")
                    if parts:
                        segments.append(
                            ParsedSegment(
                                text="\n".join(parts),
                                section=str(sheet_name),
                                extra={
                                    "source_type": "xlsx",
                                    "sheet": str(sheet_name),
                                    "row_number": int(row_number) + 1,
                                    "columns": columns,
                                },
                            )
                        )
            return segments
        except Exception as exc:
            raise ParsingError(f"XLSX parsing failed: {exc}") from exc


def _frame_to_pipe_table(frame, columns: list[str]) -> str:
    lines = [" | ".join(columns)]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if pd.isna(value):
                values.append("")
            else:
                text_value = str(value).strip()
                values.append("" if text_value.lower() == "nan" else text_value)
        if any(values):
            lines.append(" | ".join(values))
    return "\n".join(lines)
