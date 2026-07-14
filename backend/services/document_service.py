

import logging
import mimetypes
import os
from typing import Any, Dict, IO, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import FileStorage

from backend.app import db
from backend.models.document import Document, DocumentStatus, DocumentType
from backend.utils.file_validator import validate_upload, virus_scan_hook
from backend.utils.file_storage import get_storage_provider

logger = logging.getLogger("fundforge.services.document")






class DocumentError(Exception):
    
    http_status: int = 400
    error_code: str = "DOCUMENT_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DocumentNotFoundError(DocumentError):
    http_status = 404
    error_code = "DOCUMENT_NOT_FOUND"


class DocumentAccessDeniedError(DocumentError):
    http_status = 403
    error_code = "DOCUMENT_ACCESS_DENIED"


class FileValidationError(DocumentError):
    http_status = 422
    error_code = "FILE_VALIDATION_ERROR"


class VirusDetectedError(DocumentError):
    http_status = 422
    error_code = "VIRUS_DETECTED"


class StorageError(DocumentError):
    http_status = 500
    error_code = "STORAGE_ERROR"






def upload_document(
    file: FileStorage,
    user_id: str,
    document_type: str = "supporting_doc",
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    startup_id: Optional[str] = None,
    proposal_id: Optional[str] = None,
    application_id: Optional[str] = None,
    folder: str = "documents",
) -> Dict[str, Any]:
    
    original_filename = file.filename or "upload"
    declared_size = _get_content_length(file)

    
    val_result = validate_upload(
        file_stream=file.stream,
        original_filename=original_filename,
        declared_size=declared_size,
        global_max_bytes=int(os.getenv("MAX_UPLOAD_SIZE", str(25 * 1024 * 1024))),
    )

    if not val_result.is_valid:
        raise FileValidationError(
            f"File validation failed: {'; '.join(val_result.errors)}"
        )

    safe_filename = val_result.sanitised_filename
    ext           = val_result.extension
    mime          = val_result.mime_type or _guess_mime(original_filename)
    size          = declared_size

    
    try:
        doc_type = DocumentType(document_type.lower())
    except ValueError:
        doc_type = DocumentType.SUPPORTING_DOC

    
    duplicate = db.session.query(Document).filter_by(
        user_id=user_id,
        original_filename=original_filename,
        file_size_bytes=max(declared_size, 1),
        is_deleted=False
    ).first()
    if duplicate:
        logger.info("Duplicate file uploaded: %s. Reusing existing DB record.", original_filename)
        return {
            "document": duplicate.to_dict(),
            "download_url": f"/api/v1/documents/{duplicate.id}/download",
            "message": "Document already exists, reused existing record.",
        }

    
    doc = Document(
        user_id=user_id,
        startup_id=startup_id,
        proposal_id=proposal_id,
        application_id=application_id,
        original_filename=original_filename,
        storage_filename=safe_filename,
        storage_path="",  
        file_extension=ext,
        mime_type=mime,
        file_size_bytes=max(size, 1),
        document_type=doc_type,
        status=DocumentStatus.UPLOADING,
        display_name=display_name,
        description=description,
        created_by=user_id,
        updated_by=user_id,
    )
    try:
        db.session.add(doc)
        db.session.flush()  
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error creating document record: %s", exc, exc_info=True)
        raise StorageError("Failed to create document record.") from exc

    
    storage = get_storage_provider()
    file.stream.seek(0)  
    try:
        storage_path = storage.save(
            stream=file.stream,
            filename=safe_filename,
            user_id=user_id,
            folder=folder,
        )
    except Exception as exc:
        db.session.rollback()
        logger.error("Storage write failed: %s", exc, exc_info=True)
        raise StorageError(f"File storage failed: {exc}") from exc

    
    actual_size = storage.get_size(storage_path)

    
    doc.status = DocumentStatus.SCANNING
    doc.storage_path = storage_path
    doc.file_size_bytes = actual_size or max(size, 1)
    db.session.flush()

    scan_result = virus_scan_hook(
        storage._abs(storage_path)  
        if hasattr(storage, "_abs") else storage_path
    )

    if not scan_result.clean:
        logger.warning(
            "Virus detected in upload: user=%s file=%s threat=%s",
            user_id,
            original_filename,
            scan_result.threat_name,
        )
        doc.status = DocumentStatus.INFECTED
        doc.virus_scan_passed = False
        try:
            db.session.commit()
            storage.delete(storage_path)
        except Exception:
            pass
        raise VirusDetectedError(
            f"Security scan detected a threat in '{original_filename}'. "
            "The file has been quarantined."
        )

    
    doc.status = DocumentStatus.READY
    doc.virus_scan_passed = True
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB commit error after upload: %s", exc, exc_info=True)
        raise StorageError("Failed to finalise document record.") from exc

    logger.info(
        "Document uploaded: id=%s user=%s file=%s size=%d",
        doc.id, user_id, original_filename, actual_size,
    )
    return {
        "document": doc.to_dict(),
        "download_url": storage.get_url(storage_path),
        "message": f"'{original_filename}' uploaded successfully.",
    }






def download_document(
    document_id: str,
    user_id: str,
) -> Tuple[IO[bytes], str, str]:
    
    doc = _get_and_authorise(document_id, user_id)

    storage = get_storage_provider()
    try:
        stream = storage.load(doc.storage_path)
    except FileNotFoundError:
        logger.error(
            "Storage file missing: id=%s path=%s", document_id, doc.storage_path
        )
        raise StorageError("The file could not be found in storage.")

    
    try:
        doc.download_count += 1
        db.session.commit()
    except Exception:
        db.session.rollback()  

    logger.info(
        "Document downloaded: id=%s user=%s filename=%s",
        document_id, user_id, doc.original_filename,
    )
    return stream, doc.mime_type, doc.original_filename






def delete_document(document_id: str, user_id: str) -> Dict[str, str]:
    
    doc = _get_and_authorise(document_id, user_id)
    storage = get_storage_provider()

    
    
    doc.soft_delete()
    doc.updated_by = user_id
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise StorageError("Failed to delete document record.") from exc

    try:
        storage.delete(doc.storage_path)
    except FileNotFoundError:
        logger.warning(
            "Storage file already missing during delete: id=%s path=%s",
            document_id, doc.storage_path,
        )
    except Exception as exc:
        logger.error(
            "Storage delete failed for id=%s: %s", document_id, exc, exc_info=True
        )

    logger.info("Document deleted: id=%s user=%s", document_id, user_id)
    return {"message": f"Document '{doc.original_filename}' deleted successfully."}






def list_documents(
    user_id: str,
    document_type: Optional[str] = None,
    startup_id: Optional[str] = None,
    proposal_id: Optional[str] = None,
    application_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    
    per_page = min(per_page, 100)
    page = max(page, 1)

    query = (
        db.session.query(Document)
        .filter_by(user_id=user_id, is_deleted=False)
        .filter(Document.status != DocumentStatus.INFECTED)
    )

    if document_type:
        try:
            query = query.filter_by(document_type=DocumentType(document_type))
        except ValueError:
            pass  

    if startup_id:
        query = query.filter_by(startup_id=startup_id)
    if proposal_id:
        query = query.filter_by(proposal_id=proposal_id)
    if application_id:
        query = query.filter_by(application_id=application_id)
    if status:
        try:
            query = query.filter_by(status=DocumentStatus(status))
        except ValueError:
            pass

    query = query.order_by(Document.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, -(-total // per_page))

    return {
        "documents": [d.to_dict() for d in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }






def get_document_metadata(document_id: str, user_id: str) -> Dict[str, Any]:
    
    doc = _get_and_authorise(document_id, user_id)
    storage = get_storage_provider()
    return {
        "document": doc.to_dict(),
        "download_url": storage.get_url(doc.storage_path),
        "size_human": doc.size_human,
    }


def update_metadata(
    document_id: str,
    user_id: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    
    doc = _get_and_authorise(document_id, user_id)

    if display_name is not None:
        doc.display_name = display_name.strip() or None
    if description is not None:
        doc.description = description.strip() or None

    doc.updated_by = user_id
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise DocumentError("Failed to update document metadata.") from exc

    logger.info("Document metadata updated: id=%s user=%s", document_id, user_id)
    return {"document": doc.to_dict(), "message": "Document updated successfully."}






def generate_and_store_pdf(
    pdf_type: str,
    user_id: str,
    data: Dict[str, Any],
    startup_id: Optional[str] = None,
    proposal_id: Optional[str] = None,
    application_id: Optional[str] = None,
) -> Dict[str, Any]:
    
    from backend.utils.pdf_generator import (
        generate_proposal_pdf,
        generate_grant_report_pdf,
        generate_application_pdf,
        generate_startup_profile_pdf,
    )

    generators = {
        "proposal":         (generate_proposal_pdf,         DocumentType.PROPOSAL,        "proposal"),
        "grant_report":     (generate_grant_report_pdf,      DocumentType.GRANT_REPORT,    "grant_reports"),
        "application":      (generate_application_pdf,       DocumentType.APPLICATION_SUMMARY, "applications"),
        "startup_profile":  (generate_startup_profile_pdf,   DocumentType.STARTUP_PROFILE, "exports"),
    }

    if pdf_type not in generators:
        raise DocumentError(
            f"Unknown pdf_type '{pdf_type}'. "
            f"Choose one of: {', '.join(generators.keys())}."
        )

    gen_fn, doc_type, folder = generators[pdf_type]

    
    try:
        if pdf_type == "proposal":
            pdf_bytes = gen_fn(
                proposal=data.get("proposal", {}),
                grant=data.get("grant", {}),
                startup=data.get("startup", {}),
            )
        elif pdf_type == "grant_report":
            pdf_bytes = gen_fn(
                grant=data.get("grant", {}),
                match_score=data.get("match_score"),
                startup=data.get("startup"),
            )
        elif pdf_type == "application":
            pdf_bytes = gen_fn(
                application=data.get("application", {}),
                grant=data.get("grant", {}),
                startup=data.get("startup", {}),
            )
        else:  
            pdf_bytes = gen_fn(startup=data.get("startup", {}))
    except Exception as exc:
        logger.error("PDF generation failed: type=%s error=%s", pdf_type, exc, exc_info=True)
        raise DocumentError(f"PDF generation failed: {exc}") from exc

    
    import uuid as _uuid
    safe_filename = f"{_uuid.uuid4()}.pdf"
    display = _build_pdf_display_name(pdf_type, data)

    
    storage = get_storage_provider()
    import io
    try:
        storage_path = storage.save(
            stream=io.BytesIO(pdf_bytes),
            filename=safe_filename,
            user_id=user_id,
            folder=folder,
        )
    except Exception as exc:
        logger.error("PDF storage failed: %s", exc, exc_info=True)
        raise StorageError(f"PDF storage failed: {exc}") from exc

    
    doc = Document(
        user_id=user_id,
        startup_id=startup_id,
        proposal_id=proposal_id,
        application_id=application_id,
        original_filename=f"{display}.pdf",
        storage_filename=safe_filename,
        storage_path=storage_path,
        file_extension="pdf",
        mime_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        document_type=doc_type,
        status=DocumentStatus.READY,
        display_name=display,
        virus_scan_passed=True,
        created_by=user_id,
        updated_by=user_id,
    )

    try:
        db.session.add(doc)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error recording PDF document: %s", exc, exc_info=True)
        raise StorageError("Failed to record generated PDF.") from exc

    logger.info(
        "PDF generated and stored: type=%s id=%s size=%d bytes",
        pdf_type, doc.id, len(pdf_bytes),
    )
    return {
        "document": doc.to_dict(),
        "download_url": storage.get_url(storage_path),
        "message": f"{display} generated successfully.",
    }






def _get_and_authorise(document_id: str, user_id: str) -> Document:
    
    doc: Optional[Document] = db.session.get(Document, document_id)

    if doc is None or doc.is_deleted:
        raise DocumentNotFoundError(
            f"Document '{document_id}' not found."
        )

    if str(doc.user_id) != str(user_id):
        raise DocumentAccessDeniedError(
            "You do not have permission to access this document."
        )
    return doc


def _get_content_length(file: FileStorage) -> int:
    
    
    try:
        pos = file.stream.tell()
        file.stream.seek(0, 2)  
        size = file.stream.tell()
        file.stream.seek(pos)   
        return size
    except Exception:
        pass
    
    return getattr(file, "content_length", 0) or 1


def _guess_mime(filename: str) -> str:
    
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _build_pdf_display_name(pdf_type: str, data: Dict[str, Any]) -> str:
    
    labels = {
        "proposal":       lambda d: f"Proposal — {d.get('grant', {}).get('title', 'Grant')[:40]}",
        "grant_report":   lambda d: f"Grant Report — {d.get('grant', {}).get('title', 'Grant')[:40]}",
        "application":    lambda d: f"Application — {d.get('startup', {}).get('company_name', 'Company')}",
        "startup_profile": lambda d: f"Profile — {d.get('startup', {}).get('company_name', 'Company')}",
    }
    fn = labels.get(pdf_type, lambda d: "Document")
    return fn(data)
