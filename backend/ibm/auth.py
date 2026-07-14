

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests

from backend.ibm.exceptions import AIAuthError, AIConfigError, AITokenRefreshError

logger = logging.getLogger("fundforge.ibm.auth")





_IAM_URL: str = os.getenv("IBM_IAM_URL", "https://iam.cloud.ibm.com")
_TOKEN_ENDPOINT: str = f"{_IAM_URL}/identity/token"
_GRANT_TYPE: str = "urn:ibm:params:oauth:grant-type:apikey"
_REFRESH_WINDOW_SECS: int = int(os.getenv("IBM_TOKEN_REFRESH_WINDOW", "300"))
_REQUEST_TIMEOUT_SECS: int = int(os.getenv("IBM_AUTH_TIMEOUT", "30"))
_MAX_RETRIES: int = 3






@dataclass
class BearerToken:
    
    access_token: str
    expires_at: float
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        
        return time.time() >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        
        return time.time() >= (self.expires_at - _REFRESH_WINDOW_SECS)

    @property
    def authorization_header(self) -> str:
        
        return f"{self.token_type} {self.access_token}"

    def seconds_remaining(self) -> float:
        
        return self.expires_at - time.time()






class IAMTokenManager:
    

    def __init__(
        self,
        api_key: str,
        iam_url: str = _IAM_URL,
    ):
        if not api_key or not api_key.strip():
            raise AIConfigError(
                "IBM_API_KEY is not set. Cannot initialise IAM token manager.",
                provider="ibm",
            )

        self._api_key = api_key.strip()
        self._iam_url = iam_url.rstrip("/")
        self._token_endpoint = f"{self._iam_url}/identity/token"
        self._token: Optional[BearerToken] = None
        self._lock = threading.RLock()

        logger.debug("IAMTokenManager initialised for IAM URL: %s", self._iam_url)

    
    def get_token(self) -> BearerToken:
        
        with self._lock:
            if self._token is None or self._token.needs_refresh:
                self._refresh()
            return self._token  

    def get_authorization_header(self) -> str:
        
        return self.get_token().authorization_header

    def invalidate(self) -> None:
        
        with self._lock:
            self._token = None
        logger.info("IAM token cache invalidated (will re-fetch on next request).")

    def is_healthy(self) -> bool:
        
        try:
            tok = self.get_token()
            return not tok.is_expired
        except Exception:
            return False

    
    def _refresh(self) -> None:
        
        logger.info("Requesting new IAM bearer token from %s", self._token_endpoint)

        payload = {
            "grant_type": _GRANT_TYPE,
            "apikey":     self._api_key,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept":       "application/json",
        }

        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = requests.post(
                    self._token_endpoint,
                    data=payload,
                    headers=headers,
                    timeout=_REQUEST_TIMEOUT_SECS,
                )

                if response.status_code == 400:
                    raise AIAuthError(
                        "Invalid IBM API key — the key may have been revoked or expired.",
                        provider="ibm",
                        status_code=400,
                    )

                if response.status_code == 401:
                    raise AIAuthError(
                        "IBM IAM authentication failed (401). Check IBM_API_KEY.",
                        provider="ibm",
                        status_code=401,
                    )

                response.raise_for_status()
                data = response.json()

                access_token = data.get("access_token")
                expires_in   = data.get("expires_in", 3600)

                if not access_token:
                    raise AITokenRefreshError(
                        "IAM response did not contain an access_token.",
                        provider="ibm",
                    )

                self._token = BearerToken(
                    access_token=access_token,
                    expires_at=time.time() + float(expires_in),
                    token_type=data.get("token_type", "Bearer"),
                )

                logger.info(
                    "IAM token obtained successfully — expires in %.0fs.",
                    self._token.seconds_remaining(),
                )
                return

            except (AIAuthError, AITokenRefreshError):
                raise  

            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning(
                    "IAM token request timed out (attempt %d/%d).", attempt, _MAX_RETRIES
                )

            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "IAM token request failed (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc
                )

            if attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)  

        raise AITokenRefreshError(
            f"Failed to obtain IAM token after {_MAX_RETRIES} attempts: {last_exc}",
            provider="ibm",
        ) from last_exc






_manager_instance: Optional[IAMTokenManager] = None
_manager_lock = threading.Lock()


def get_token_manager(api_key: Optional[str] = None) -> IAMTokenManager:
    
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            key = api_key or os.getenv("IBM_API_KEY", "")
            _manager_instance = IAMTokenManager(api_key=key)
        return _manager_instance


def reset_token_manager() -> None:
    
    global _manager_instance
    with _manager_lock:
        _manager_instance = None
