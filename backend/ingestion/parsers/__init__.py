from pathlib import Path

from ingestion.exceptions import UnsupportedFileError
from ingestion.parsers.csv_parser import CsvParser
from ingestion.parsers.docx_parser import DocxParser
from ingestion.parsers.pdf_parser import PdfParser
from ingestion.parsers.txt_parser import TxtParser
from ingestion.parsers.xlsx_parser import XlsxParser

UNSUPPORTED_FORMATS_MESSAGE = (
    "Unsupported file format. Supported formats: PDF, DOCX, TXT, XLSX, CSV."
)

PARSER_REGISTRY = {
    "pdf": PdfParser(),
    "docx": DocxParser(),
    "csv": CsvParser(),
    "txt": TxtParser(),
    "xlsx": XlsxParser(),
}


def get_parser(file_type: str):
    parser = PARSER_REGISTRY.get((file_type or "").lower())
    if parser is None:
        raise UnsupportedFileError(UNSUPPORTED_FORMATS_MESSAGE)
    return parser


def parse_file(file_path: Path, file_type: str):
    parser = get_parser(file_type)
    return parser.parse(Path(file_path))
