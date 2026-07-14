

import logging
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Dict, List, Optional

logger = logging.getLogger("fundforge.utils.file_storage")





class StorageProvider(ABC):
    

    @abstractmethod
    def save(
        self,
        stream: IO[bytes],
        filename: str,
        user_id: str,
        folder: str = "documents",
    ) -> str:
        pass

    @abstractmethod
    def load(self, storage_path: str) -> IO[bytes]:
        pass

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        pass

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        pass

    @abstractmethod
    def get_url(self, storage_path: str, expires_seconds: int = 3600) -> str:
        pass

    @abstractmethod
    def get_size(self, storage_path: str) -> int:
        pass

    @abstractmethod
    def list_user_files(self, user_id: str, folder: str = "documents") -> List[Dict]:
        pass

    def user_folder(self, user_id: str, folder: str) -> str:
        
        return f"users/{user_id}/{folder}"






class LocalStorageProvider(StorageProvider):
    

    def __init__(self, base_dir: Optional[str] = None):
        self._base = Path(
            base_dir or os.getenv("UPLOAD_FOLDER", "uploads")
        ).resolve()
        self._base.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorageProvider initialised: base_dir=%s", self._base)

    
    def save(
        self,
        stream: IO[bytes],
        filename: str,
        user_id: str,
        folder: str = "documents",
    ) -> str:
        
        dest_dir = self._base / "users" / user_id / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        
        tmp_path = dest_dir / f".tmp_{uuid.uuid4()}"
        try:
            with open(tmp_path, "wb") as fh:
                shutil.copyfileobj(stream, fh)
            os.replace(tmp_path, dest_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

        rel_path = str(dest_path.relative_to(self._base))
        logger.info(
            "File saved: user=%s folder=%s path=%s size=%d bytes",
            user_id,
            folder,
            rel_path,
            dest_path.stat().st_size,
        )
        return rel_path

    
    def load(self, storage_path: str) -> IO[bytes]:
        
        abs_path = self._abs(storage_path)
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        return open(abs_path, "rb")

    
    def delete(self, storage_path: str) -> None:
        
        abs_path = self._abs(storage_path)
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        abs_path.unlink()
        logger.info("File deleted: %s", storage_path)

    
    def exists(self, storage_path: str) -> bool:
        return self._abs(storage_path).exists()

    
    def get_url(self, storage_path: str, expires_seconds: int = 3600) -> str:
        
        return f"/api/v1/documents/file/{storage_path}"

    
    def get_size(self, storage_path: str) -> int:
        abs_path = self._abs(storage_path)
        if not abs_path.exists():
            return 0
        return abs_path.stat().st_size

    
    def list_user_files(self, user_id: str, folder: str = "documents") -> List[Dict]:
        
        user_dir = self._base / "users" / user_id / folder
        if not user_dir.exists():
            return []

        files = []
        for p in sorted(user_dir.iterdir()):
            if p.is_file() and not p.name.startswith("."):
                stat = p.stat()
                files.append({
                    "filename": p.name,
                    "storage_path": str(p.relative_to(self._base)),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(
                        stat.st_ctime, tz=timezone.utc
                    ).isoformat(),
                })
        return files

    
    def _abs(self, storage_path: str) -> Path:
        
        candidate = (self._base / storage_path).resolve()
        if not str(candidate).startswith(str(self._base)):
            raise ValueError(
                f"Attempted path traversal: '{storage_path}' resolves outside base_dir."
            )
        return candidate






_provider_instance: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    backend = os.getenv("STORAGE_BACKEND", "local").lower().strip()

    if backend == "local":
        _provider_instance = LocalStorageProvider()
    elif backend == "s3":
        raise NotImplementedError(
            "S3StorageProvider is not yet implemented. "
            "Set STORAGE_BACKEND=local or provide an S3StorageProvider class."
        )
    elif backend == "gcs":
        raise NotImplementedError(
            "GCSStorageProvider is not yet implemented. "
            "Set STORAGE_BACKEND=local or provide a GCSStorageProvider class."
        )
    else:
        logger.warning(
            "Unknown STORAGE_BACKEND '%s'; falling back to local.", backend
        )
        _provider_instance = LocalStorageProvider()

    return _provider_instance


def reset_storage_provider() -> None:
    
    global _provider_instance
    _provider_instance = None
