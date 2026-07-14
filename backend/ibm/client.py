

import logging
import os
import threading
import time
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.ibm.exceptions import (
    AICircuitOpenError,
    AIConnectionError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)

logger = logging.getLogger("fundforge.ibm.client")





_IBM_URL: str = os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com")


_CONNECT_TIMEOUT: float = float(os.getenv("IBM_CONNECT_TIMEOUT", "10"))
_READ_TIMEOUT: float    = float(os.getenv("IBM_READ_TIMEOUT",    "120"))  


_MAX_RETRIES: int          = int(os.getenv("IBM_MAX_RETRIES",   "3"))
_BACKOFF_FACTOR: float     = float(os.getenv("IBM_BACKOFF",     "1.5"))
_RETRY_STATUS_CODES        = (429, 500, 502, 503, 504)


_POOL_CONNECTIONS: int = int(os.getenv("IBM_POOL_CONNECTIONS", "5"))
_POOL_MAXSIZE: int     = int(os.getenv("IBM_POOL_MAXSIZE",     "20"))


_CB_FAILURE_THRESHOLD: int  = int(os.getenv("IBM_CB_FAILURE_THRESHOLD", "5"))
_CB_RESET_TIMEOUT_SECS: int = int(os.getenv("IBM_CB_RESET_TIMEOUT",    "60"))






class CircuitBreaker:
    

    _CLOSED    = "CLOSED"
    _OPEN      = "OPEN"
    _HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = _CB_FAILURE_THRESHOLD,
        reset_timeout: int = _CB_RESET_TIMEOUT_SECS,
        name: str = "ibm",
    ):
        self._threshold   = failure_threshold
        self._timeout     = reset_timeout
        self._name        = name
        self._state       = self._CLOSED
        self._failures    = 0
        self._opened_at: Optional[float] = None
        self._lock        = threading.RLock()

    
    def call(self, fn, *args, **kwargs):
        
        with self._lock:
            if self._state == self._OPEN:
                if time.time() - self._opened_at >= self._timeout:
                    self._state = self._HALF_OPEN
                    logger.info("[CB:%s] HALF_OPEN — probing service.", self._name)
                else:
                    remaining = int(self._timeout - (time.time() - self._opened_at))
                    raise AICircuitOpenError(
                        f"Circuit breaker is OPEN for '{self._name}'. "
                        f"Service appears unavailable. Retry in ~{remaining}s.",
                        provider="ibm",
                        reset_after=remaining,
                    )

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except AICircuitOpenError:
            raise
        except Exception as exc:
            self._on_failure(exc)
            raise

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == self._CLOSED

    
    def _on_success(self) -> None:
        with self._lock:
            if self._state == self._HALF_OPEN:
                logger.info("[CB:%s] CLOSED — service recovered.", self._name)
            self._state    = self._CLOSED
            self._failures = 0
            self._opened_at = None

    def _on_failure(self, exc: Exception) -> None:
        with self._lock:
            self._failures += 1
            logger.warning(
                "[CB:%s] Failure %d/%d: %s",
                self._name, self._failures, self._threshold, exc,
            )
            if self._failures >= self._threshold:
                self._state = self._OPEN
                self._opened_at = time.time()
                logger.error(
                    "[CB:%s] OPEN after %d failures. Will probe in %ds.",
                    self._name, self._failures, self._timeout,
                )






class IBMHttpClient:
    

    def __init__(
        self,
        base_url: str = _IBM_URL,
        api_key: Optional[str] = None,
    ):
        from backend.ibm.auth import get_token_manager
        self._base_url = base_url.rstrip("/")
        self._token_manager = get_token_manager(api_key=api_key)
        self._circuit_breaker = CircuitBreaker(name="ibm-watsonx")
        self._session = self._build_session()
        logger.info("IBMHttpClient initialised: base_url=%s", self._base_url)

    
    def get(self, path: str, **kwargs) -> requests.Response:
        
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        
        return self._request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        
        return self._request("DELETE", path, **kwargs)

    
    def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[tuple] = None,
        **kwargs,
    ) -> requests.Response:
        
        url = self._build_url(path)
        merged_headers = self._build_headers(extra=headers)
        effective_timeout = timeout or (_CONNECT_TIMEOUT, _READ_TIMEOUT)

        def _do_request():
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    timeout=effective_timeout,
                    **kwargs,
                )
                return self._handle_response(response, method, url)
            except requests.exceptions.Timeout as exc:
                raise AITimeoutError(
                    f"Request timed out: {method} {url}",
                    provider="ibm",
                ) from exc
            except requests.exceptions.ConnectionError as exc:
                raise AIConnectionError(
                    f"Connection failed: {method} {url} — {exc}",
                    provider="ibm",
                ) from exc

        try:
            return self._circuit_breaker.call(_do_request)
        except (AICircuitOpenError, AITimeoutError, AIConnectionError):
            raise
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                f"Unexpected error during {method} {url}: {exc}",
                provider="ibm",
            ) from exc

    def _handle_response(
        self,
        response: requests.Response,
        method: str,
        url: str,
    ) -> requests.Response:
        
        log_extra = {
            "method": method,
            "url":    url,
            "status": response.status_code,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 1),
        }

        if response.status_code < 300:
            logger.debug("IBM API call OK: %s", log_extra)
            return response

        
        if response.status_code == 401:
            logger.warning("IBM API 401 — invalidating token cache.")
            self._token_manager.invalidate()
            from backend.ibm.exceptions import AIAuthError
            raise AIAuthError(
                "IBM API returned 401. Token may have expired — please retry.",
                provider="ibm",
                status_code=401,
            )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise AIRateLimitError(
                f"IBM API rate limit exceeded. Retry after {retry_after}s.",
                provider="ibm",
                status_code=429,
                retry_after=retry_after,
            )

        
        try:
            body = response.json()
            msg = (
                body.get("errors", [{}])[0].get("message")
                or body.get("message")
                or body.get("error")
                or f"HTTP {response.status_code}"
            )
        except Exception:
            msg = f"HTTP {response.status_code}"

        logger.error("IBM API error: %s", {**log_extra, "body": response.text[:500]})
        raise AIProviderError(
            f"IBM API error: {msg}",
            provider="ibm",
            status_code=response.status_code,
            details={"url": url, "method": method},
        )

    
    def _build_url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{self._base_url}{path}"

    def _build_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        
        auth_header = self._token_manager.get_authorization_header()
        headers = {
            "Authorization": auth_header,
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _build_session(self) -> requests.Session:
        
        session = requests.Session()
        retry = Retry(
            total=_MAX_RETRIES,
            backoff_factor=_BACKOFF_FACTOR,
            status_forcelist=_RETRY_STATUS_CODES,
            allowed_methods={"GET", "POST", "DELETE"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            pool_connections=_POOL_CONNECTIONS,
            pool_maxsize=_POOL_MAXSIZE,
            max_retries=retry,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        
        return self._circuit_breaker






_client_instance: Optional[IBMHttpClient] = None
_client_lock = threading.Lock()


def get_ibm_client(base_url: Optional[str] = None) -> IBMHttpClient:
    
    global _client_instance
    with _client_lock:
        if _client_instance is None:
            _client_instance = IBMHttpClient(
                base_url=base_url or os.getenv("IBM_URL", _IBM_URL)
            )
        return _client_instance


def reset_ibm_client() -> None:
    
    global _client_instance
    with _client_lock:
        _client_instance = None
