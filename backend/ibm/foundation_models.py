

import logging
import os
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from backend.ibm.exceptions import AIConfigError, AIModelError, AIProviderError

logger = logging.getLogger("fundforge.ibm.foundation_models")





@dataclass
class GenerationParameters:
    
    model_id: str = ""
    max_new_tokens: int = 1024
    min_new_tokens: int = 10
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = False

    def to_ibm_params(self) -> Dict[str, Any]:
        
        params: Dict[str, Any] = {
            "decoding_method":    "sample" if self.temperature > 0 else "greedy",
            "max_new_tokens":     self.max_new_tokens,
            "min_new_tokens":     self.min_new_tokens,
            "temperature":        self.temperature,
            "top_p":              self.top_p,
            "top_k":              self.top_k,
            "repetition_penalty": self.repetition_penalty,
        }
        if self.stop_sequences:
            params["stop_sequences"] = self.stop_sequences
        return params


@dataclass
class GenerationResult:
    
    text: str
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    fallback_used: bool = False
    response_time_ms: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ModelInfo:
    
    model_id: str
    label: str
    provider: str
    description: str = ""
    max_sequence_length: int = 0
    is_available: bool = True






class BaseAIProvider(ABC):
    

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> GenerationResult:
        pass

    @abstractmethod
    def generate_text_stream(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        pass


AIProvider = BaseAIProvider






_IBM_API_VERSION: str = os.getenv("IBM_API_VERSION", "2024-05-31")
_GENERATION_PATH      = "/ml/v1/text/generation"
_GENERATION_STREAM_PATH = "/ml/v1/text/generation_stream"
_MODEL_SPECS_PATH     = "/ml/v1/foundation_model_specs"


class IBMProvider(BaseAIProvider):
    

    def __init__(
        self,
        project_id: Optional[str] = None,
        default_model_id: Optional[str] = None,
    ):
        from backend.ibm.client import get_ibm_client

        self._project_id = (
            project_id or os.getenv("IBM_PROJECT_ID", "")
        ).strip()
        self._default_model_id = (
            default_model_id
            or os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2")
        )

        if not self._project_id:
            raise AIConfigError(
                "IBM_PROJECT_ID is not set. Cannot initialise IBMProvider.",
                provider="ibm",
            )

        self._client = get_ibm_client()
        logger.info(
            "IBMProvider initialised — project_id=%s model=%s",
            self._project_id[:8] + "...",
            self._default_model_id,
        )

    
    @property
    def provider_name(self) -> str:
        return "ibm"

    def generate_text(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> GenerationResult:
        
        eff_params = params or GenerationParameters(model_id=self._default_model_id)
        model_id = eff_params.model_id or self._default_model_id

        payload = {
            "model_id":   model_id,
            "project_id": self._project_id,
            "input":      prompt,
            "parameters": eff_params.to_ibm_params(),
        }

        logger.debug(
            "IBM generate_text: model=%s max_new_tokens=%d prompt_chars=%d",
            model_id, eff_params.max_new_tokens, len(prompt),
        )

        try:
            response = self._client.post(
                _GENERATION_PATH,
                json=payload,
                params={"version": _IBM_API_VERSION},
            )
            return self._parse_generation_response(response.json(), model_id)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIModelError(
                f"Text generation failed: {exc}",
                provider="ibm",
            ) from exc

    def generate_text_stream(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        
        eff_params = params or GenerationParameters(model_id=self._default_model_id)
        model_id = eff_params.model_id or self._default_model_id

        payload = {
            "model_id":   model_id,
            "project_id": self._project_id,
            "input":      prompt,
            "parameters": eff_params.to_ibm_params(),
        }

        logger.debug(
            "IBM generate_text_stream: model=%s prompt_chars=%d",
            model_id, len(prompt),
        )

        try:
            import json as _json
            response = self._client._session.post(
                self._client._build_url(_GENERATION_STREAM_PATH),
                json=payload,
                params={"version": _IBM_API_VERSION},
                headers=self._client._build_headers(),
                stream=True,
                timeout=(_IBM_CONNECT_TIMEOUT, _IBM_STREAM_TIMEOUT),
            )
            response.raise_for_status()

            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line in ("[DONE]", ""):
                    break
                try:
                    chunk = _json.loads(line)
                    generated = chunk.get("results", [{}])[0].get("generated_text", "")
                    if generated:
                        yield generated
                except _json.JSONDecodeError:
                    continue

        except AIProviderError:
            raise
        except Exception as exc:
            raise AIModelError(
                f"Streaming generation failed: {exc}",
                provider="ibm",
            ) from exc

    def list_models(self) -> List[ModelInfo]:
        
        try:
            response = self._client.get(
                _MODEL_SPECS_PATH,
                params={
                    "version": _IBM_API_VERSION,
                    "project_id": self._project_id,
                },
            )
            data = response.json()
            resources = data.get("resources", [])
            models = []
            for r in resources:
                models.append(ModelInfo(
                    model_id=r.get("model_id", ""),
                    label=r.get("label", r.get("model_id", "")),
                    provider="ibm",
                    description=r.get("description", ""),
                    max_sequence_length=r.get("model_limits", {}).get("max_sequence_length", 0),
                ))
            logger.info("IBM model list retrieved: %d models.", len(models))
            return models
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                f"Failed to list IBM models: {exc}",
                provider="ibm",
            ) from exc

    def is_healthy(self) -> bool:
        
        try:
            self._client._token_manager.get_token()
            return self._client.circuit_breaker.is_closed
        except Exception:
            return False

    
    @staticmethod
    def _parse_generation_response(
        body: Dict[str, Any],
        model_id: str,
    ) -> GenerationResult:
        
        try:
            result_block = body.get("results", [{}])[0]
            return GenerationResult(
                text=result_block.get("generated_text", ""),
                model_id=model_id,
                input_tokens=result_block.get("input_token_count", 0),
                output_tokens=result_block.get("generated_token_count", 0),
                stop_reason=result_block.get("stop_reason", ""),
                raw=body,
            )
        except (IndexError, KeyError) as exc:
            raise AIModelError(
                f"Unexpected IBM generation response shape: {exc}",
                provider="ibm",
            ) from exc






_IBM_CONNECT_TIMEOUT: float = float(os.getenv("IBM_CONNECT_TIMEOUT", "10"))
_IBM_STREAM_TIMEOUT:  float = float(os.getenv("IBM_STREAM_TIMEOUT",  "300"))






class GeminiProvider(BaseAIProvider):
    

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self._model_id = "gemini-1.5-flash"

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate_text(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> GenerationResult:
        if not self._api_key:
            raise AIConfigError("GEMINI_API_KEY is not set.", provider="gemini")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model_id}:generateContent?key={self._api_key}"
        eff_params = params or GenerationParameters()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": eff_params.temperature,
                "maxOutputTokens": eff_params.max_new_tokens,
                "topP": eff_params.top_p,
                "topK": eff_params.top_k,
            }
        }
        try:
            res = requests.post(url, json=payload, timeout=30)
            res.raise_for_status()
            res_json = res.json()
            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            input_tokens = res_json.get("usageMetadata", {}).get("promptTokenCount", 0)
            output_tokens = res_json.get("usageMetadata", {}).get("candidatesTokenCount", 0)
            return GenerationResult(
                text=text,
                model_id=self._model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                raw=res_json,
            )
        except Exception as e:
            raise AIModelError(f"Gemini generation failed: {e}", provider="gemini") from e

    def generate_text_stream(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        if not self._api_key:
            raise AIConfigError("GEMINI_API_KEY is not set.", provider="gemini")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model_id}:streamGenerateContent?key={self._api_key}"
        eff_params = params or GenerationParameters()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": eff_params.temperature,
                "maxOutputTokens": eff_params.max_new_tokens,
                "topP": eff_params.top_p,
                "topK": eff_params.top_k,
            }
        }
        try:
            res = requests.post(url, json=payload, timeout=30, stream=True)
            res.raise_for_status()
            import json as _json
            for line in res.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("[") or line_str.startswith(","):
                    line_str = line_str[1:].strip()
                if line_str.endswith("]"):
                    line_str = line_str[:-1].strip()
                if not line_str:
                    continue
                try:
                    obj = _json.loads(line_str)
                    part_text = obj["candidates"][0]["content"]["parts"][0]["text"]
                    if part_text:
                        yield part_text
                except Exception:
                    continue
        except Exception as e:
            raise AIModelError(f"Gemini streaming failed: {e}", provider="gemini") from e

    def list_models(self) -> List[ModelInfo]:
        return [ModelInfo(model_id=self._model_id, label="Gemini 1.5 Flash", provider="gemini")]

    def is_healthy(self) -> bool:
        return bool(self._api_key)


class GrokProvider(BaseAIProvider):
    

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = (api_key or os.getenv("GROQ_API_KEY", "")).strip()
        self._model_id = "llama-3.1-8b-instant"

    @property
    def provider_name(self) -> str:
        return "grok"

    def generate_text(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> GenerationResult:
        if not self._api_key:
            raise AIConfigError("GROQ_API_KEY is not set.", provider="grok")
        url = "https://api.groq.com/openai/v1/chat/completions"
        eff_params = params or GenerationParameters()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": eff_params.temperature,
            "max_tokens": eff_params.max_new_tokens,
            "top_p": eff_params.top_p,
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()
            res_json = res.json()
            text = res_json["choices"][0]["message"]["content"]
            input_tokens = res_json.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = res_json.get("usage", {}).get("completion_tokens", 0)
            return GenerationResult(
                text=text,
                model_id=self._model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                raw=res_json,
            )
        except Exception as e:
            raise AIModelError(f"Groq/Grok generation failed: {e}", provider="grok") from e

    def generate_text_stream(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        if not self._api_key:
            raise AIConfigError("GROQ_API_KEY is not set.", provider="grok")
        url = "https://api.groq.com/openai/v1/chat/completions"
        eff_params = params or GenerationParameters()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": eff_params.temperature,
            "max_tokens": eff_params.max_new_tokens,
            "top_p": eff_params.top_p,
            "stream": True
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30, stream=True)
            res.raise_for_status()
            import json as _json
            for line in res.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data:"):
                    line_str = line_str[5:].strip()
                if line_str == "[DONE]":
                    break
                if not line_str:
                    continue
                try:
                    obj = _json.loads(line_str)
                    delta = obj["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue
        except Exception as e:
            raise AIModelError(f"Groq/Grok streaming failed: {e}", provider="grok") from e

    def list_models(self) -> List[ModelInfo]:
        return [ModelInfo(model_id=self._model_id, label="Llama 3 8B (Groq)", provider="grok")]

    def is_healthy(self) -> bool:
        return bool(self._api_key)


class FallbackManager(BaseAIProvider):
    

    def __init__(
        self,
        ibm_provider: IBMProvider,
        gemini_provider: GeminiProvider,
        grok_provider: GrokProvider,
    ):
        self._ibm = ibm_provider
        self._gemini = gemini_provider
        self._grok = grok_provider
        self.last_active_provider = "IBM"
        self.last_fallback_used = False
        self.last_response_time_ms = 0.0

    @property
    def provider_name(self) -> str:
        return "fallback"

    def generate_text(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> GenerationResult:
        import time
        start_time = time.perf_counter()
        
        
        try:
            logger.info("Attempting text generation with primary provider (IBM watsonx)...")
            res = self._ibm.generate_text(prompt, params)
            duration = (time.perf_counter() - start_time) * 1000
            
            
            self.last_active_provider = "IBM"
            self.last_fallback_used = False
            self.last_response_time_ms = duration
            
            res.provider = "IBM"
            res.fallback_used = False
            res.response_time_ms = duration
            
            logger.info(
                "AI Request completed - requested_provider: IBM, actual_provider_used: IBM, fallback_used: False, fallback_reason: None, execution_time_ms: %.2f",
                duration
            )
            return res
        except Exception as exc:
            fallback_reason = str(exc)
            logger.warning(
                "IBM watsonx failed (fallback condition met), trying Gemini fallback. Error: %s",
                fallback_reason
            )
            logger.warning(
                "AI Request Fallback Event - requested_provider: IBM, fallback_target: Gemini, fallback_reason: %s",
                fallback_reason
            )

        
        try:
            logger.info("Attempting text generation with Gemini fallback...")
            res = self._gemini.generate_text(prompt, params)
            duration = (time.perf_counter() - start_time) * 1000
            
            
            self.last_active_provider = "Gemini"
            self.last_fallback_used = True
            self.last_response_time_ms = duration
            
            res.provider = "Gemini"
            res.fallback_used = True
            res.response_time_ms = duration
            
            logger.info(
                "AI Request completed - requested_provider: IBM, actual_provider_used: Gemini, fallback_used: True, fallback_reason: %s, execution_time_ms: %.2f",
                fallback_reason, duration
            )
            return res
        except Exception as exc:
            second_reason = str(exc)
            logger.warning(
                "Gemini failed, trying Grok fallback. Error: %s",
                second_reason
            )
            logger.warning(
                "AI Request Fallback Event - requested_provider: Gemini, fallback_target: Grok, fallback_reason: %s",
                second_reason
            )

        
        try:
            logger.info("Attempting text generation with Grok fallback...")
            res = self._grok.generate_text(prompt, params)
            duration = (time.perf_counter() - start_time) * 1000
            
            
            self.last_active_provider = "Grok"
            self.last_fallback_used = True
            self.last_response_time_ms = duration
            
            res.provider = "Grok"
            res.fallback_used = True
            res.response_time_ms = duration
            
            logger.info(
                "AI Request completed - requested_provider: IBM, actual_provider_used: Grok, fallback_used: True, fallback_reason: %s, execution_time_ms: %.2f",
                fallback_reason + " | " + second_reason, duration
            )
            return res
        except Exception as exc:
            final_duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                "AI Request Failed - requested_provider: IBM, actual_provider_used: None, chain_failure: True, execution_time_ms: %.2f",
                final_duration
            )
            raise AIModelError(
                f"All AI providers in the fallback chain failed. IBM error: {fallback_reason}. Gemini error: {second_reason}. Grok error: {exc}",
                provider="fallback"
            ) from exc

    def generate_text_stream(
        self,
        prompt: str,
        params: Optional[GenerationParameters] = None,
    ) -> Iterator[str]:
        import time
        start_time = time.perf_counter()
        
        
        try:
            logger.info("Attempting streaming with primary provider (IBM watsonx)...")
            generator = self._ibm.generate_text_stream(prompt, params)
            first_chunk = next(generator)
            duration = (time.perf_counter() - start_time) * 1000
            
            self.last_active_provider = "IBM"
            self.last_fallback_used = False
            self.last_response_time_ms = duration
            
            logger.info(
                "AI Stream completed initiation - requested_provider: IBM, actual_provider_used: IBM, fallback_used: False, execution_time_ms: %.2f",
                duration
            )
            
            def _stream_wrapper(first, gen):
                yield first
                for chunk in gen:
                    yield chunk
            return _stream_wrapper(first_chunk, generator)
        except Exception as exc:
            fallback_reason = str(exc)
            logger.warning(
                "IBM watsonx streaming failed, trying Gemini fallback. Error: %s",
                fallback_reason
            )
            logger.warning(
                "AI Stream Fallback Event - requested_provider: IBM, fallback_target: Gemini, fallback_reason: %s",
                fallback_reason
            )

        
        try:
            logger.info("Attempting streaming with Gemini fallback...")
            generator = self._gemini.generate_text_stream(prompt, params)
            first_chunk = next(generator)
            duration = (time.perf_counter() - start_time) * 1000
            
            self.last_active_provider = "Gemini"
            self.last_fallback_used = True
            self.last_response_time_ms = duration
            
            logger.info(
                "AI Stream completed initiation - requested_provider: IBM, actual_provider_used: Gemini, fallback_used: True, execution_time_ms: %.2f",
                duration
            )
            
            def _stream_wrapper(first, gen):
                yield first
                for chunk in gen:
                    yield chunk
            return _stream_wrapper(first_chunk, generator)
        except Exception as exc:
            second_reason = str(exc)
            logger.warning(
                "Gemini streaming failed, trying Grok fallback. Error: %s",
                second_reason
            )
            logger.warning(
                "AI Stream Fallback Event - requested_provider: Gemini, fallback_target: Grok, fallback_reason: %s",
                second_reason
            )

        
        try:
            logger.info("Attempting streaming with Grok fallback...")
            generator = self._grok.generate_text_stream(prompt, params)
            first_chunk = next(generator)
            duration = (time.perf_counter() - start_time) * 1000
            
            self.last_active_provider = "Grok"
            self.last_fallback_used = True
            self.last_response_time_ms = duration
            
            logger.info(
                "AI Stream completed initiation - requested_provider: IBM, actual_provider_used: Grok, fallback_used: True, execution_time_ms: %.2f",
                duration
            )
            
            def _stream_wrapper(first, gen):
                yield first
                for chunk in gen:
                    yield chunk
            return _stream_wrapper(first_chunk, generator)
        except Exception as exc:
            final_duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                "AI Stream Request Failed - requested_provider: IBM, actual_provider_used: None, chain_failure: True, execution_time_ms: %.2f",
                final_duration
            )
            raise AIModelError(
                f"All AI streaming providers in the fallback chain failed. IBM error: {fallback_reason}. Gemini error: {second_reason}. Grok error: {exc}",
                provider="fallback"
            ) from exc

    def list_models(self) -> List[ModelInfo]:
        models = []
        try:
            models.extend(self._ibm.list_models())
        except Exception:
            pass
        try:
            models.extend(self._gemini.list_models())
        except Exception:
            pass
        try:
            models.extend(self._grok.list_models())
        except Exception:
            pass
        return models

    def is_healthy(self) -> bool:
        return self._ibm.is_healthy() or self._gemini.is_healthy() or self._grok.is_healthy()


FallbackAIProvider = FallbackManager






_PROVIDER_REGISTRY: Dict[str, type] = {
    "ibm": IBMProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "fallback": FallbackManager,
}

_provider_singleton: Optional[BaseAIProvider] = None
_provider_lock = __import__("threading").Lock()


class ProviderFactory:
    

    @staticmethod
    def get_provider(
        provider_name: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseAIProvider:
        global _provider_singleton
        with _provider_lock:
            if _provider_singleton is None:
                name = (
                    provider_name
                    or os.getenv("AI_PROVIDER", "fallback")
                ).lower().strip()

                if name == "ibm":
                    name = "fallback"

                if name == "fallback":
                    ibm = IBMProvider(**kwargs)
                    gemini = GeminiProvider()
                    grok = GrokProvider()
                    _provider_singleton = FallbackManager(ibm, gemini, grok)
                    logger.info("AI Provider initialized with transparent fallback chain: IBM -> Gemini -> Grok")
                else:
                    cls = _PROVIDER_REGISTRY.get(name)
                    if cls is None:
                        raise AIConfigError(
                            f"AI provider '{name}' is not registered. "
                            f"Available providers: {list(_PROVIDER_REGISTRY.keys())}",
                            provider=name,
                        )
                    _provider_singleton = cls(**kwargs)
                    logger.info("AI provider initialised: %s", name)

            return _provider_singleton


def get_ai_provider(
    provider_name: Optional[str] = None,
    **kwargs: Any,
) -> BaseAIProvider:
    
    return ProviderFactory.get_provider(provider_name, **kwargs)


def reset_ai_provider() -> None:
    
    global _provider_singleton
    with _provider_lock:
        _provider_singleton = None


def register_provider(name: str, cls: type) -> None:
    
    if not (isinstance(cls, type) and issubclass(cls, BaseAIProvider)):
        raise TypeError(f"{cls} must be a subclass of BaseAIProvider.")
    _PROVIDER_REGISTRY[name] = cls
    logger.info("AI provider registered: %s → %s", name, cls.__name__)
