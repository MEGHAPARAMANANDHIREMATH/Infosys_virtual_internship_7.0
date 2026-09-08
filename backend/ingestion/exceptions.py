class DocumentProcessingError(Exception):
    """Base class for document pipeline failures."""


class UnsupportedFileError(DocumentProcessingError):
    pass


class FileTooLargeError(DocumentProcessingError):
    pass


class EmptyDocumentError(DocumentProcessingError):
    pass


class ParsingError(DocumentProcessingError):
    pass


class EmbeddingError(DocumentProcessingError):
    pass


class VectorStoreError(DocumentProcessingError):
    pass


class SearchError(Exception):
    pass
