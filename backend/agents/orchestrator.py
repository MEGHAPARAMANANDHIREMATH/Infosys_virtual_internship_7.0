import hashlib
import logging

from documents.models import Document, ProcessingStatus
from documents.serializers import DocumentSerializer
from documents.services import hash_uploaded_file, store_uploaded_file
from ingestion.exceptions import EmptyDocumentError, EmptyFileError, FileTooLargeError, UnsupportedFileError
from ingestion.parsers import UNSUPPORTED_FORMATS_MESSAGE
from ingestion.processor import process_document

from agents.blocker_agent import BlockerActionAgent
from agents.constants import AGENT_ALL, AGENT_BLOCKERS, AGENT_RISK, AGENT_SCOPE, VALID_AGENTS
from agents.exceptions import AgentAnalysisError
from agents.models import DocumentAnalysis
from agents.risk_agent import RiskForecastAgent
from agents.scope_agent import ScopeDeliverableAgent
from agents.text import extract_document_text
from django.conf import settings

logger = logging.getLogger("agents")

AGENTS = {
    AGENT_SCOPE: ScopeDeliverableAgent(),
    AGENT_RISK: RiskForecastAgent(),
    AGENT_BLOCKERS: BlockerActionAgent(),
}


def normalize_agent_keys(raw) -> list[str]:
    if raw is None or raw == "" or raw == AGENT_ALL:
        return [AGENT_SCOPE, AGENT_RISK, AGENT_BLOCKERS]
    if isinstance(raw, str):
        values = [part.strip().lower() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, list):
        values = [str(part).strip().lower() for part in raw]
    else:
        raise AgentAnalysisError("Invalid agent selection.")
    mapped = []
    aliases = {
        "scope": AGENT_SCOPE,
        "scope & deliverables": AGENT_SCOPE,
        "deliverables": AGENT_SCOPE,
        "risk": AGENT_RISK,
        "risks": AGENT_RISK,
        "forecast": AGENT_RISK,
        "risk & delivery forecast": AGENT_RISK,
        "blockers": AGENT_BLOCKERS,
        "actions": AGENT_BLOCKERS,
        "blockers & action items": AGENT_BLOCKERS,
        "all": AGENT_ALL,
    }
    for value in values:
        key = aliases.get(value, value)
        if key == AGENT_ALL:
            return [AGENT_SCOPE, AGENT_RISK, AGENT_BLOCKERS]
        if key not in VALID_AGENTS or key == AGENT_ALL:
            raise AgentAnalysisError(
                "Unknown agent. Choose scope, risk, blockers, or all."
            )
        if key not in mapped:
            mapped.append(key)
    if not mapped:
        raise AgentAnalysisError("Select at least one agent.")
    return mapped


def run_intelligence(document: Document, agent_keys: list[str]) -> dict:
    if document.processing_status != ProcessingStatus.PROCESSED:
        raise AgentAnalysisError(
            document.error_message
            or "The document has not been processed successfully and cannot be analyzed."
        )
    try:
        text = extract_document_text(document.file_path, document.file_type)
    except EmptyDocumentError:
        raise
    except Exception as exc:
        logger.exception("Text extraction failed document_id=%s", document.id)
        raise AgentAnalysisError("Could not read the uploaded document.") from exc

    if not text.strip():
        raise EmptyDocumentError("No readable text was found in this document.")

    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    metadata = {
        "file_name": document.file_name,
        "file_type": document.file_type,
        "document_id": document.id,
    }
    errors = {}
    scope_result = None
    risk_bundle = None
    blockers_result = None
    provider = "openai" if _provider_name() == "openai" else "grounded"

    if AGENT_SCOPE in agent_keys:
        try:
            logger.info("Running scope agent document_id=%s", document.id)
            scope_result = AGENTS[AGENT_SCOPE].analyze(text, metadata)
        except Exception as exc:
            logger.exception("Scope agent failed")
            errors["scope"] = "Scope analysis failed. Please retry."

    if AGENT_RISK in agent_keys:
        try:
            logger.info("Running risk agent document_id=%s", document.id)
            meta = dict(metadata)
            if scope_result:
                meta["scope_result"] = scope_result
            risk_bundle = AGENTS[AGENT_RISK].analyze(text, meta)
        except Exception as exc:
            logger.exception("Risk agent failed")
            errors["risk"] = "Risk analysis failed. Please retry."

    if AGENT_BLOCKERS in agent_keys:
        try:
            logger.info("Running blocker agent document_id=%s", document.id)
            blockers_result = AGENTS[AGENT_BLOCKERS].analyze(text, metadata)
        except Exception as exc:
            logger.exception("Blocker agent failed")
            errors["blockers"] = "Blocker analysis failed. Please retry."

    analysis = DocumentAnalysis.objects.create(
        document=document,
        project=document.project,
        content_hash=content_hash,
        provider=provider,
        requested_agents=agent_keys,
        scope_result=scope_result,
        risk_result=(risk_bundle or {}).get("risks") if risk_bundle else None,
        forecast_result=(risk_bundle or {}).get("forecast") if risk_bundle else None,
        blockers_result=blockers_result,
        error_message="; ".join(errors.values()),
    )
    return serialize_analysis(
        document,
        analysis,
        agent_keys,
        duplicate=False,
        errors=errors,
        text_chars=len(text),
    )


def serialize_analysis(document, analysis, agent_keys, duplicate=False, errors=None, text_chars=None):
    payload = {
        "document_id": document.id,
        "file_name": document.file_name,
        "file_type": document.file_type,
        "duplicate": duplicate,
        "provider": analysis.provider,
        "agents_run": agent_keys,
        "analysis_id": analysis.id,
        "scope": analysis.scope_result,
        "risks": analysis.risk_result,
        "forecast": analysis.forecast_result,
        "blockers": analysis.blockers_result,
        "errors": errors or {},
        "processing_status": "completed" if not (errors or {}) else "completed_with_errors",
    }
    if text_chars is not None:
        payload["extracted_characters"] = text_chars
    return payload


def latest_analysis(document: Document) -> dict | None:
    analysis = document.analyses.order_by("-created_at").first()
    if not analysis:
        return None
    return serialize_analysis(document, analysis, analysis.requested_agents)


def ingest_uploaded_file(project, uploaded):
    from pathlib import Path

    extension = Path(uploaded.name).suffix.lower().lstrip(".")
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileError(UNSUPPORTED_FORMATS_MESSAGE)
    if uploaded.size == 0:
        raise EmptyFileError("The uploaded file is empty.")
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if uploaded.size > max_bytes:
        raise FileTooLargeError(
            f"File is too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB."
        )
    file_hash = hash_uploaded_file(uploaded)
    existing = (
        Document.objects.filter(
            project=project,
            file_hash=file_hash,
            processing_status=ProcessingStatus.PROCESSED,
        )
        .order_by("-uploaded_at")
        .first()
    )
    if existing:
        return existing, True
    stored_path = store_uploaded_file(project.id, uploaded)
    document = Document.objects.create(
        project=project,
        file_name=uploaded.name,
        file_type=extension,
        file_path=str(stored_path),
        processing_status="UPLOADED",
        file_hash=file_hash,
    )
    process_document(document)
    document.refresh_from_db()
    return document, False


def _provider_name() -> str:
    from agents.llm import llm_enabled

    return "openai" if llm_enabled() else "grounded"
