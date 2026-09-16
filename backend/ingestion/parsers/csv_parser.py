from pathlib import Path

import pandas as pd

from ingestion.exceptions import ParsingError
from ingestion.parsers.base import ParsedSegment


class CsvParser:
    def parse(self, file_path: Path) -> list[ParsedSegment]:
        try:
            frame = pd.read_csv(file_path)
            segments: list[ParsedSegment] = []
            columns = [str(col) for col in frame.columns]
            if columns:
                header_lines = [" | ".join(columns)]
                for _, row in frame.iterrows():
                    values = []
                    for column in columns:
                        value = row[column]
                        if pd.isna(value):
                            values.append("")
                        else:
                            values.append(str(value).strip())
                    if any(values):
                        header_lines.append(" | ".join(values))
                segments.append(
                    ParsedSegment(
                        text="\n".join(header_lines),
                        extra={"source_type": "csv_table", "columns": columns},
                    )
                )
            for row_number, row in frame.iterrows():
                parts = []
                for column in columns:
                    value = row[column]
                    if pd.isna(value):
                        continue
                    text_value = str(value).strip()
                    if text_value:
                        parts.append(f"{column}: {text_value}")
                if parts:
                    segments.append(
                        ParsedSegment(
                            text="\n".join(parts),
                            extra={
                                "source_type": "csv",
                                "row_number": int(row_number) + 1,
                                "columns": columns,
                            },
                        )
                    )
            return segments
        except Exception as exc:
            raise ParsingError(f"CSV parsing failed: {exc}") from exc
