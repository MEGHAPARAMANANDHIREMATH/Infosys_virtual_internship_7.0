# Milestone 1 data model

## Project

id, name, description, start_date, end_date, status, created_by, created_at

## Document

id, project_id, file_name, file_type, file_path, processing_status (`UPLOADED` | `PROCESSING` | `PROCESSED` | `FAILED`), uploaded_at, error_message

## DocumentChunk

id, document_id, project_id, content, chunk_index, page_number, section, embedding_reference

## ChromaDB metadata

embedding, chunk content, document_id, project_id, chunk_id, page_number, file_name
