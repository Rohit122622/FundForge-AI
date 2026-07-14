

import logging
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import IO, Dict, FrozenSet, List, Optional, Tuple

logger = logging.getLogger("fundforge.utils.file_validator")






_KB = 1024
_MB = _KB * 1024


_SIZE_LIMITS: Dict[str, int] = {
    "pdf":  int(os.getenv("MAX_PDF_SIZE",  str(25 * _MB))),
    "docx": int(os.getenv("MAX_DOCX_SIZE", str(25 * _MB))),
    "pptx": int(os.getenv("MAX_PPTX_SIZE", str(50 * _MB))),
    "txt":  int(os.getenv("MAX_TXT_SIZE",  str(5  * _MB))),
    "png":  int(os.getenv("MAX_IMG_SIZE",  str(10 * _MB))),
    "jpg":  int(os.getenv("MAX_IMG_SIZE",  str(10 * _MB))),
    "jpeg": int(os.getenv("MAX_IMG_SIZE",  str(10 * _MB))),
}


_ALLOWED_MIME_MAP: Dict[str, FrozenSet[str]] = {
    "pdf":  frozenset({"application/pdf"}),
    "docx": frozenset({
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  
    }),
    "pptx": frozenset({
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    }),
    "txt":  frozenset({"text/plain"}),
    "png":  frozenset({"image/png"}),
    "jpg":  frozenset({"image/jpeg"}),
    "jpeg": frozenset({"image/jpeg"}),
}


_SAFE_STEM_RE = re.compile(r"[^\w\-. ]")


_MAX_STEM_LENGTH = 200






@dataclass
class FileValidationResult:
    
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    sanitised_filename: str = ""
    original_filename: str = ""
    extension: str = ""
    mime_type: str = ""
    file_size: int = 0

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "sanitised_filename": self.sanitised_filename,
            "original_filename": self.original_filename,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
        }






def validate_upload(
    file_stream: IO[bytes],
    original_filename: str,
    declared_size: int,
    allowed_extensions: Optional[FrozenSet[str]] = None,
    global_max_bytes: int = 25 * _MB,
) -> FileValidationResult:
    
    result = FileValidationResult(original_filename=original_filename)
    errors: List[str] = []

    
    clean_name, ext = sanitise_filename(original_filename)
    result.sanitised_filename = clean_name
    result.extension = ext

    if not ext:
        errors.append(
            f"File '{original_filename}' has no extension. "
            "A recognised extension is required."
        )
        result.errors = errors
        return result

    
    effective_allowed = allowed_extensions or frozenset(_ALLOWED_MIME_MAP.keys())
    if ext not in effective_allowed:
        errors.append(
            f"Extension '.{ext}' is not allowed. "
            f"Permitted types: {', '.join(sorted(effective_allowed))}."
        )
        result.errors = errors
        return result

    
    result.file_size = declared_size
    type_limit = _SIZE_LIMITS.get(ext, global_max_bytes)
    effective_limit = min(type_limit, global_max_bytes)

    if declared_size > effective_limit:
        errors.append(
            f"File size {_fmt_bytes(declared_size)} exceeds the limit of "
            f"{_fmt_bytes(effective_limit)} for .{ext} files."
        )

    
    mime = _detect_mime(file_stream)
    result.mime_type = mime

    
    if mime:
        allowed_mimes = _ALLOWED_MIME_MAP.get(ext, frozenset())
        if mime not in allowed_mimes:
            errors.append(
                f"File content (MIME: {mime}) does not match the declared "
                f"extension '.{ext}'. Possible extension spoofing detected."
            )

    result.errors = errors
    result.is_valid = len(errors) == 0

    logger.debug(
        "File validation: filename=%s ext=%s mime=%s size=%d valid=%s errors=%s",
        original_filename,
        ext,
        mime,
        declared_size,
        result.is_valid,
        errors or "none",
    )
    return result


def sanitise_filename(original: str) -> Tuple[str, str]:
    
    if not original:
        ext = ""
        return f"{uuid.uuid4()}.bin", ext

    
    normalised = unicodedata.normalize("NFKC", original)

    
    basename = os.path.basename(normalised)
    basename = basename.replace("..", "").replace("/", "").replace("\\", "")

    
    if "." in basename:
        stem, raw_ext = basename.rsplit(".", 1)
        ext = raw_ext.lower().strip()
    else:
        stem = basename
        ext = ""

    
    safe_stem = _SAFE_STEM_RE.sub("_", stem)
    safe_stem = safe_stem.strip(". _")[:_MAX_STEM_LENGTH] or "upload"

    
    uid = str(uuid.uuid4())
    if ext:
        safe_filename = f"{uid}.{ext}"
    else:
        safe_filename = uid

    return safe_filename, ext


def is_allowed_extension(filename: str, allowed: Optional[FrozenSet[str]] = None) -> bool:
    
    _, ext = sanitise_filename(filename)
    effective = allowed or frozenset(_ALLOWED_MIME_MAP.keys())
    return ext in effective


def get_allowed_extensions() -> FrozenSet[str]:
    
    return frozenset(_ALLOWED_MIME_MAP.keys())


def get_mime_map() -> Dict[str, FrozenSet[str]]:
    
    return dict(_ALLOWED_MIME_MAP)






class VirusScanResult:
    

    def __init__(self, clean: bool, threat_name: Optional[str] = None):
        self.clean = clean
        self.threat_name = threat_name

    def __bool__(self) -> bool:
        return self.clean


def virus_scan_hook(file_path: str) -> VirusScanResult:
    
    logger.info("Virus scan hook called for: %s (stub — no scanner configured)", file_path)
    
    return VirusScanResult(clean=True)






def _detect_mime(file_stream: IO[bytes]) -> str:
    
    try:
        import magic  
        pos = file_stream.tell()
        header = file_stream.read(2048)
        file_stream.seek(pos)  
        mime = magic.from_buffer(header, mime=True)
        return mime or ""
    except ImportError:
        logger.warning(
            "python-magic is not installed — MIME type validation skipped. "
            "Install with: pip install python-magic"
        )
        return ""
    except Exception as exc:
        logger.warning("MIME detection failed: %s", exc)
        return ""


def _fmt_bytes(n: int) -> str:
    
    if n >= _MB:
        return f"{n / _MB:.1f} MB"
    if n >= _KB:
        return f"{n / _KB:.1f} KB"
    return f"{n} B"
