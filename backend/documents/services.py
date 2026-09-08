import logging
from pathlib import Path

from django.conf import settings

from documents.models import Document
from rag.vector_store import get_vector_store

logger = logging.getLogger("documents")


def store_uploaded_file(project_id: int, uploaded_file) -> Path:
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    target_dir = Path(settings.MEDIA_ROOT) / "uploads" / str(project_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / uploaded_file.name
    counter = 1
    while destination.exists():
        destination = target_dir / f"{destination.stem}_{counter}{destination.suffix}"
        counter += 1
    with destination.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)
    return destination


def delete_document_artifacts(document: Document) -> None:
    get_vector_store().delete_by_document(document.id)
    path = Path(document.file_path)
    if path.exists():
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Could not delete file %s: %s", path, exc)


def delete_project_artifacts(project) -> None:
    get_vector_store().delete_by_project(project.id)
    for document in project.documents.all():
        path = Path(document.file_path)
        if path.exists():
            try:
                path.unlink()
            except OSError as exc:
                logger.warning("Could not delete file %s: %s", path, exc)
